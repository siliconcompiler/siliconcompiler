# Copyright 2022 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy
import csv
import gzip
import json
import logging
import os
import re
import pathlib
import argparse
import sys
import shlex

try:
    import yaml
    _has_yaml = True
except ImportError:
    _has_yaml = False

from .schema_cfg import schema_cfg
from .utils import escape_val_tcl, PACKAGE_ROOT, translate_loglevel


class Schema:
    """Object for storing and accessing configuration values corresponding to
    the SiliconCompiler schema.

    Most user-facing interaction with the schema should occur through an
    instance of :class:`~siliconcompiler.core.Chip`, but this class is available
    for schema manipulation tasks that don't require the additional context of a
    Chip object.

    The two arguments to this class are mutually exclusive. If neither are
    provided, the object is initialized to default values for all parameters.

    Args:
        cfg (dict): Initial configuration dictionary. This may be a subtree of
            the schema.
        manifest (str): Initial manifest.
        logger (logging.Logger): instance of the parent logger if available
    """

    # Special key in node dict that represents a value corresponds to a
    # global default for all steps/indices.
    GLOBAL_KEY = 'global'
    PERNODE_FIELDS = ('value', 'filehash', 'date', 'author', 'signature', 'package')

    def __init__(self, cfg=None, manifest=None, logger=None):
        if cfg is not None and manifest is not None:
            raise ValueError('You may not specify both cfg and manifest')

        self._init_logger(logger)

        self._stop_journal()

        if manifest is not None:
            # Normalize value to string in case we receive a pathlib.Path
            cfg, self.__journal = Schema.__read_manifest_file(str(manifest))
        else:
            cfg = copy.deepcopy(cfg)

        if cfg is not None:
            try:
                if Schema.__dict_requires_normalization(cfg):
                    cfg = Schema.__dict_to_schema(cfg)
                self.cfg = cfg
            except (TypeError, ValueError) as e:
                raise ValueError('Attempting to read manifest with '
                                 f'incompatible schema version: {e}') \
                    from e
        else:
            self.cfg = self._init_schema_cfg()

    ###########################################################################
    def _init_schema_cfg(self):
        return schema_cfg()

    ###########################################################################
    @staticmethod
    def __dict_to_schema_set(cfg, *key):
        if Schema._is_leaf(cfg):
            for field, value in cfg.items():
                if field == 'node':
                    for step, substep in value.items():
                        if step == 'default':
                            continue
                        for index, values in substep.items():
                            if step == Schema.GLOBAL_KEY:
                                sstep = None
                            else:
                                sstep = step
                            if index == Schema.GLOBAL_KEY:
                                sindex = None
                            else:
                                sindex = index
                            for nodefield, nodevalue in values.items():
                                Schema.__set(*key, nodevalue,
                                             cfg=cfg,
                                             field=nodefield,
                                             step=sstep, index=sindex)
                else:
                    Schema.__set(*key, value, cfg=cfg, field=field)
        else:
            for nextkey, subcfg in cfg.items():
                Schema.__dict_to_schema_set(subcfg, *key, nextkey)

    ###########################################################################
    @staticmethod
    def __dict_to_schema(cfg):
        for category, subcfg in cfg.items():
            if category in ('history', 'library'):
                # History and library are subschemas
                for _, value in subcfg.items():
                    Schema.__dict_to_schema(value)
            else:
                Schema.__dict_to_schema_set(subcfg, category)
        return cfg

    ###########################################################################
    @staticmethod
    def __dict_requires_normalization(cfg):
        '''
        Recurse over scheme configuration to check for tuples
        Returns: False if dict is correct, True is dict requires normalization,
            None if tuples were not found
        '''
        if Schema._is_leaf(cfg):
            if '(' in cfg['type']:
                for step, substep in cfg['node'].items():
                    for index, values in substep.items():
                        values = values['value']
                        if not values:
                            continue
                        if isinstance(values, list):
                            for v in values:
                                if isinstance(v, tuple):
                                    return False
                        if isinstance(values, tuple):
                            return False
                        return True
            else:
                return None
        else:
            for subcfg in cfg.values():
                ret = Schema.__dict_requires_normalization(subcfg)
                if ret is None:
                    continue
                else:
                    return ret

    ###########################################################################
    def _merge_with_init_schema(self):
        new_schema = Schema()

        for keylist in self.allkeys():
            if keylist[0] in ('history', 'library'):
                continue

            if 'default' in keylist:
                continue

            # only read in valid keypaths without 'default'
            key_valid = new_schema.valid(*keylist, default_valid=True)
            if not key_valid:
                self.logger.warning(f'Keypath {keylist} is not valid')
            if not key_valid:
                continue

            for val, step, index in self._getvals(*keylist, return_defvalue=False):
                new_schema.set(*keylist, val, step=step, index=index)

                # update other pernode fields
                # TODO: only update these if clobber is successful
                step_key = Schema.GLOBAL_KEY if not step else step
                idx_key = Schema.GLOBAL_KEY if not index else index
                for field in self.getdict(*keylist)['node'][step_key][idx_key].keys():
                    if field == 'value':
                        continue
                    new_schema.set(*keylist,
                                   self.get(*keylist, step=step, index=index, field=field),
                                   step=step, index=index, field=field)

        if 'library' in self.cfg:
            # Handle libraries separately
            for library in self.cfg['library'].keys():
                lib_schema = Schema(cfg=self.getdict('library', library))
                lib_schema._merge_with_init_schema()
                new_schema.cfg['library'][library] = lib_schema.cfg

        if 'history' in self.cfg:
            # Copy over history
            new_schema.cfg['history'] = self.cfg['history']

        self.cfg = new_schema.cfg

    ###########################################################################
    @staticmethod
    def __read_manifest_file(filepath):
        if not os.path.isfile(filepath):
            raise ValueError(f'Manifest file not found {filepath}')

        if os.path.splitext(filepath)[1].lower() == '.gz':
            fin = gzip.open(filepath, 'r')
        else:
            fin = open(filepath, 'r')

        try:
            if re.search(r'(\.json|\.sup)(\.gz)*$', filepath, flags=re.IGNORECASE):
                localcfg = json.load(fin)
            elif re.search(r'(\.yaml|\.yml)(\.gz)*$', filepath, flags=re.IGNORECASE):
                if not _has_yaml:
                    raise ImportError('yaml package required to read YAML manifest')
                localcfg = yaml.load(fin, Loader=yaml.SafeLoader)
            else:
                raise ValueError(f'File format not recognized {filepath}')
        finally:
            fin.close()

        journal = None
        try:
            if '__journal__' in localcfg:
                journal = localcfg['__journal__']
                del localcfg['__journal__']
        except (TypeError, ValueError) as e:
            raise ValueError(f'Attempting to read manifest with incompatible schema version: {e}') \
                from e

        return localcfg, journal

    def get(self, *keypath, field='value', job=None, step=None, index=None):
        """
        Returns a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.get` for detailed documentation.
        """
        # Prevent accidental modifications of the schema content by not passing a reference
        return copy.copy(self.__get(*keypath, field=field, job=job, step=step, index=index))

    ###########################################################################
    def __get(self, *keypath, field='value', job=None, step=None, index=None):
        cfg = self.__search(*keypath, job=job)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: get() '
                             'must be called on a complete keypath')

        err = Schema.__validate_step_index(cfg['pernode'], field, step, index)
        if err:
            raise ValueError(f'Invalid args to get() of keypath {keypath}: {err}')

        if isinstance(index, int):
            index = str(index)

        if field in self.PERNODE_FIELDS:
            try:
                return cfg['node'][step][index][field]
            except KeyError:
                if cfg['pernode'] == 'required':
                    return cfg['node']['default']['default'][field]

            try:
                return cfg['node'][step][self.GLOBAL_KEY][field]
            except KeyError:
                pass

            try:
                return cfg['node'][self.GLOBAL_KEY][self.GLOBAL_KEY][field]
            except KeyError:
                return cfg['node']['default']['default'][field]
        elif field in cfg:
            return cfg[field]
        else:
            raise ValueError(f'Invalid field {field}')

    ###########################################################################
    def set(self, *args, field='value', clobber=True, step=None, index=None):
        '''
        Sets a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.set` for detailed documentation.
        '''

        keypath = args[:-1]
        cfg = self.__search(*keypath, insert_defaults=True)

        return self.__set(*args, logger=self.logger, cfg=cfg, field=field, clobber=clobber,
                          step=step, index=index, journal_callback=self.__record_journal)

    ###########################################################################
    @staticmethod
    def __set(*args, logger=None, cfg=None, field='value', clobber=True,
              step=None, index=None,
              journal_callback=None):
        '''
        Sets a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.set` for detailed documentation.
        '''
        keypath = args[:-1]
        value = args[-1]

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: set() '
                             'must be called on a complete keypath')

        err = Schema.__validate_step_index(cfg['pernode'], field, step, index)
        if err:
            raise ValueError(f'Invalid args to set() of keypath {keypath}: {err}')

        if isinstance(index, int):
            index = str(index)

        if cfg['lock'] and field != 'lock':
            if logger:
                logger.debug(f'Failed to set value for {keypath}: parameter is locked')
            return False

        if Schema.__is_set(cfg, step=step, index=index) and not clobber:
            if logger:
                logger.debug(f'Failed to set value for {keypath}: clobber is False '
                             'and parameter is set')
            return False

        allowed_values = None
        if 'enum' in cfg:
            allowed_values = cfg['enum']

        value = Schema.__check_and_normalize(value, cfg['type'], field, keypath, allowed_values)

        if journal_callback:
            journal_callback("set", keypath,
                             value=value,
                             field=field,
                             step=step, index=index)

        if field in Schema.PERNODE_FIELDS:
            step = step if step is not None else Schema.GLOBAL_KEY
            index = index if index is not None else Schema.GLOBAL_KEY

            if step not in cfg['node']:
                cfg['node'][step] = {}
            if index not in cfg['node'][step]:
                cfg['node'][step][index] = copy.deepcopy(cfg['node']['default']['default'])
            cfg['node'][step][index][field] = value
        else:
            cfg[field] = value

        return True

    ###########################################################################
    def add(self, *args, field='value', step=None, index=None):
        '''
        Adds item(s) to a schema parameter list.

        See :meth:`~siliconcompiler.core.Chip.add` for detailed documentation.
        '''
        keypath = args[:-1]

        cfg = self.__search(*keypath, insert_defaults=True)

        return self._add(*args, cfg=cfg, field=field, step=step, index=index)

    ###########################################################################
    def _add(self, *args, cfg=None, field='value', step=None, index=None, package=None):
        '''
        Adds item(s) to a schema parameter list.

        See :meth:`~siliconcompiler.core.Chip.add` for detailed documentation.
        '''
        keypath = args[:-1]
        value = args[-1]

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: add() '
                             'must be called on a complete keypath')

        err = Schema.__validate_step_index(cfg['pernode'], field, step, index)
        if err:
            raise ValueError(f'Invalid args to add() of keypath {keypath}: {err}')

        if isinstance(index, int):
            index = str(index)

        if not Schema.__is_list(field, cfg['type']):
            if field == 'value':
                raise ValueError(f'Invalid keypath {keypath}: add() must be called on a list')
            else:
                raise ValueError(f'Invalid field {field}: add() must be called on a list')

        if cfg['lock']:
            self.logger.debug(f'Failed to set value for {keypath}: parameter is locked')
            return False

        allowed_values = None
        if 'enum' in cfg:
            allowed_values = cfg['enum']

        value = Schema.__check_and_normalize(value, cfg['type'], field, keypath, allowed_values)
        self.__record_journal("add", keypath, value=value, field=field, step=step, index=index)
        if field in self.PERNODE_FIELDS:
            modified_step = step if step is not None else self.GLOBAL_KEY
            modified_index = index if index is not None else self.GLOBAL_KEY

            if modified_step not in cfg['node']:
                cfg['node'][modified_step] = {}
            if modified_index not in cfg['node'][modified_step]:
                cfg['node'][modified_step][modified_index] = copy.deepcopy(
                    cfg['node']['default']['default'])
            cfg['node'][modified_step][modified_index][field].extend(value)
        else:
            cfg[field].extend(value)

        return True

    ###########################################################################
    def change_type(self, *key, type=None):
        '''
        Change the type of a key

        Args:
            key (list): Key to change.
            type (str): New data type for this key

        Examples:
            >>> chip.set('option', 'var', 'run_test', 'true')
            >>> chip.schema.change_type('option', 'var', 'run_test', 'bool')
            Changes the type of ['option', 'var', 'run_test'] to a boolean.
        '''

        if not type:
            raise ValueError('Type cannot be empty')

        if 'file' in type or 'dir' in type:
            raise ValueError(f'Cannot convert to {type}')

        cfg = self.__search(*key, insert_defaults=True)
        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {key}: change_type() '
                             'must be called on a complete keypath')

        old_type = self.get(*key, field='type')
        if 'file' in old_type or 'dir' in old_type:
            raise ValueError(f'Cannot convert from {old_type}')

        old_type_is_list = '[' in old_type
        new_type_is_list = '[' in type

        if 'file' in old_type or 'dir' in old_type:
            raise ValueError(f'Cannot convert from {type}')

        new_values = []
        for values, step, index in [*self._getvals(*key),
                                    (self.get_default(*key), 'default', 'default')]:
            if old_type_is_list and not new_type_is_list:
                # Old type is list, but new type in not a list
                # Can only convert if list has 1 or 0 elements
                if len(values) > 1:
                    raise ValueError(f'Too many values in {",".join(key)} to convert a '
                                     'list of a scalar.')
                if len(values) == 1:
                    values = values[0]
                else:
                    values = None

            if new_type_is_list and values is None:
                values = []

            new_values.append((step, index, values))

        self.set(*key, type, field='type')
        for step, index, values in new_values:
            if step == 'default' and index == 'default':
                self.set_default(*key, values)
            else:
                self.set(*key, values, step=step, index=index)

    ###########################################################################
    def remove(self, *keypath):
        '''
        Remove a keypath

        See :meth:`~siliconcompiler.core.Chip.remove` for detailed documentation.
        '''
        search_path = keypath[0:-1]
        removal_key = keypath[-1]

        if removal_key == 'default':
            self.logger.error(f'Cannot remove default keypath: {keypath}')
            return

        cfg = self.__search(*search_path)
        if 'default' not in cfg:
            self.logger.error(f'Cannot remove a non-default keypath: {keypath}')
            return

        if removal_key not in cfg:
            self.logger.error(f'Key does not exist: {keypath}')
            return

        for key in self.allkeys(*keypath):
            fullpath = [*keypath, *key]
            if self.get(*fullpath, field='lock'):
                self.logger.error(f'Key is locked: {fullpath}')
                return

        del cfg[removal_key]
        self.__record_journal("remove", keypath)

    ###########################################################################
    def unset(self, *keypath, step=None, index=None):
        '''
        Unsets a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.unset` for detailed documentation.
        '''
        cfg = self.__search(*keypath)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: unset() '
                             'must be called on a complete keypath')

        err = Schema.__validate_step_index(cfg['pernode'], 'value', step, index)
        if err:
            raise ValueError(f'Invalid args to unset() of keypath {keypath}: {err}')

        if isinstance(index, int):
            index = str(index)

        if cfg['lock']:
            self.logger.debug(f'Failed to set value for {keypath}: parameter is locked')
            return False

        if step is None:
            step = Schema.GLOBAL_KEY
        if index is None:
            index = Schema.GLOBAL_KEY

        try:
            del cfg['node'][step][index]
            self.__record_journal("unset", keypath, step=step, index=index)
        except KeyError:
            # If this key doesn't exist, silently continue - it was never set
            pass

        return True

    def _getvals(self, *keypath, return_defvalue=True):
        """
        Returns all values (global and pernode) associated with a particular parameter.

        Returns a list of tuples of the form (value, step, index). The list is
        in no particular order. For the global value, step and index are None.
        If return_defvalue is True, the default parameter value is added to the
        list in place of a global value if a global value is not set.
        """
        cfg = self.__search(*keypath)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: _getvals() '
                             'must be called on a complete keypath')

        vals = []
        has_global = False
        for step in cfg['node']:
            if step == 'default':
                continue

            for index in cfg['node'][step]:
                step_arg = None if step == self.GLOBAL_KEY else step
                index_arg = None if index == self.GLOBAL_KEY else index
                if 'value' in cfg['node'][step][index]:
                    if step_arg is None and index_arg is None:
                        has_global = True
                    vals.append((cfg['node'][step][index]['value'], step_arg, index_arg))

        if (cfg['pernode'] != 'required') and not has_global and return_defvalue:
            vals.append((cfg['node']['default']['default']['value'], None, None))

        return vals

    ###########################################################################
    def getkeys(self, *keypath, job=None):
        """
        Returns a list of schema dictionary keys.

        See :meth:`~siliconcompiler.core.Chip.getkeys` for detailed documentation.
        """
        cfg = self.__search(*keypath, job=job)
        keys = list(cfg.keys())

        if 'default' in keys:
            keys.remove('default')

        return keys

    ###########################################################################
    def getdict(self, *keypath):
        """
        Returns a schema dictionary.

        See :meth:`~siliconcompiler.core.Chip.getdict` for detailed
        documentation.
        """
        cfg = self.__search(*keypath)
        return copy.deepcopy(cfg)

    ###########################################################################
    def valid(self, *args, default_valid=False, job=None):
        """
        Checks validity of a keypath.

        See :meth:`~siliconcompiler.core.Chip.valid` for detailed
        documentation.
        """
        keylist = list(args)
        if default_valid:
            default = 'default'
        else:
            default = None

        if job is not None:
            cfg = self.cfg['history'][job]
        else:
            cfg = self.cfg

        for key in keylist:
            if key in cfg:
                cfg = cfg[key]
            elif default_valid and default in cfg:
                cfg = cfg[default]
            else:
                return False
        return Schema._is_leaf(cfg)

    ##########################################################################
    def has_field(self, *args):
        keypath = args[:-1]
        field = args[-1]

        cfg = self.__search(*keypath)
        return field in cfg

    ##########################################################################
    def record_history(self):
        '''
        Copies all non-empty parameters from current job into the history
        dictionary.
        '''

        # initialize new dict
        jobname = self.get('option', 'jobname')
        self.cfg['history'][jobname] = {}

        # copy in all empty values of scope job
        allkeys = self.allkeys()
        for key in allkeys:
            # ignore history in case of cumulative history
            if key[0] != 'history':
                scope = self.get(*key, field='scope')
                if not self.is_empty(*key) and (scope == 'job'):
                    self.__copyparam(self.cfg,
                                     self.cfg['history'][jobname],
                                     key)

    @staticmethod
    def __check_and_normalize(value, sc_type, field, keypath, allowed_values):
        '''
        This method validates that user-provided values match the expected type,
        and returns a normalized version of the value.

        The expected type is based on the schema parameter type string for
        value-related fields, and is based on the field itself for other fields.
        This function raises a TypeError if an illegal value is provided.

        The normalization process provides some leeway in how users supply
        values, while ensuring that values are stored consistently in the schema.

        The normalization rules are as follows:
        - If a scalar is provided for a list type, it is promoted to a list of
        one element.
        - If a list is provided for a tuple type, it is cast to a tuple (since
        the JSON module serializes tuples as arrays, which are deserialized into
        lists).
        - Elements inside lists and tuples are normalized recursively.
        - All non-list values have a string representation that gets cast to a
        native Python type (since we receive strings from the CLI):
          - bool: accepts "true" or "false"
          - ints and floats: cast as if by int() or float()
          - tuples: accepts comma-separated values surrounded by parens
        '''

        if value is None and not Schema.__is_list(field, sc_type):
            # None is legal for all scalars, but not within collection types
            # TODO: could consider normalizing "None" for lists to empty list?
            return value

        if field == 'value':
            # Push down error_msg from the top since arguments get modified in recursive call
            error_msg = f'Invalid value {value} for keypath {keypath}: expected type {sc_type}'
            return Schema._normalize_value(value, sc_type, error_msg, allowed_values)
        else:
            return Schema.__normalize_field(value, sc_type, field, keypath)

    @staticmethod
    def _normalize_value(value, sc_type, error_msg, allowed_values):
        if sc_type.startswith('['):
            base_type = sc_type[1:-1]

            # Need to try 2 different recursion strategies - if value is a list already, then we can
            # recurse on it directly. However, if that doesn't work, then it might be a
            # list-of-lists/tuples that needs to be wrapped in an outer list, so we try that.
            if isinstance(value, (list, set, tuple)):
                try:
                    return [Schema._normalize_value(v, base_type, error_msg, allowed_values)
                            for v in value]
                except TypeError:
                    pass

            value = [value]
            return [Schema._normalize_value(v, base_type, error_msg, allowed_values) for v in value]

        if sc_type.startswith('('):
            # TODO: make parsing more robust to support tuples-of-tuples
            if isinstance(value, str):
                value = value[1:-1].split(',')
            elif not (isinstance(value, tuple) or isinstance(value, list)):
                raise TypeError(error_msg)

            base_types = sc_type[1:-1].split(',')
            if len(value) != len(base_types):
                raise TypeError(error_msg)
            return tuple(Schema._normalize_value(v, base_type, error_msg, allowed_values)
                         for v, base_type in zip(value, base_types))

        if sc_type == 'bool':
            if value == 'true':
                return True
            if value == 'false':
                return False
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            raise TypeError(error_msg)

        try:
            if sc_type == 'int':
                return int(value)

            if sc_type == 'float':
                return float(value)
        except TypeError:
            raise TypeError(error_msg) from None

        if sc_type == 'str':
            if isinstance(value, str):
                return value
            elif isinstance(value, bool):
                return str(value).lower()
            elif isinstance(value, (list, tuple)):
                raise TypeError(error_msg)
            else:
                return str(value)

        if sc_type in ('file', 'dir'):
            if isinstance(value, (str, pathlib.Path)):
                return str(value)
            else:
                raise TypeError(error_msg)

        if sc_type == 'enum':
            if isinstance(value, str):
                if value in allowed_values:
                    return value
                valid = ", ".join(allowed_values)
                raise ValueError(error_msg + f", and value of {valid}")
            else:
                raise TypeError(error_msg)

        raise ValueError(f'Invalid type specifier: {sc_type}')

    @staticmethod
    def __normalize_field(value, sc_type, field, keypath):
        def error_msg(t):
            return f'Invalid value {value} for field {field} of keypath {keypath}: expected {t}'

        if field in ('author', 'date') and ('file' not in sc_type):
            raise TypeError(f'Invalid field {field} for keypath {keypath}: '
                            'this field only exists for file parameters')

        if field in ('copy', 'filehash', 'package', 'hashalgo') and \
           ('file' not in sc_type and 'dir' not in sc_type):
            raise TypeError(f'Invalid field {field} for keypath {keypath}: '
                            'this field only exists for file and dir parameters')

        is_list = Schema.__is_list(field, sc_type)
        if field == 'package' and is_list:
            if not isinstance(value, list):
                value = [value]
            if not all((v is None or isinstance(v, (str, pathlib.Path))) for v in value):
                raise TypeError(error_msg('None, str or pathlib.Path'))
            return value

        if is_list:
            if not value:
                # Replace none with an empty list
                value = []

            if not isinstance(value, list):
                value = [value]

            if not all(isinstance(v, str) for v in value):
                raise TypeError(error_msg('str'))
            return value

        if field == 'scope':
            # Restricted allowed values
            if not (isinstance(value, str) and value in ('global', 'job', 'scratch')):
                raise TypeError(error_msg('one of "global", "job", or "scratch"'))
            return value

        if field == 'pernode':
            # Restricted allowed values
            if not (isinstance(value, str) and value in ('never', 'optional', 'required')):
                raise TypeError(f'Invalid value {value} for field {field}: '
                                'expected one of "never", "optional", or "required"')
            return value

        if field in (
            'type', 'switch', 'shorthelp', 'help', 'unit', 'hashalgo', 'notes',
            'signature'
        ):
            if not isinstance(value, str):
                raise TypeError(error_msg('str'))
            return value

        if field in ('lock', 'copy', 'require'):
            if value == 'true':
                return True
            if value == 'false':
                return False
            if isinstance(value, bool):
                return value
            else:
                raise TypeError(error_msg('bool'))

        if field in ('node',):
            if isinstance(value, dict):
                return value
            else:
                raise TypeError(f'Invalid value {value} for field {field}: expected dict')

        raise ValueError(f'Invalid field {field} for keypath {keypath}')

    @staticmethod
    def __is_set(cfg, step=None, index=None):
        '''Returns whether a user has set a value for this parameter.

        A value counts as set if a user has set a global value OR a value for
        the provided step/index.
        '''
        if Schema.GLOBAL_KEY in cfg['node'] and \
           Schema.GLOBAL_KEY in cfg['node'][Schema.GLOBAL_KEY] and \
           'value' in cfg['node'][Schema.GLOBAL_KEY][Schema.GLOBAL_KEY]:
            # global value is set
            return True

        if step is None:
            return False
        if index is None:
            index = Schema.GLOBAL_KEY

        return step in cfg['node'] and \
            index in cfg['node'][step] and \
            'value' in cfg['node'][step][index]

    @staticmethod
    def _is_leaf(cfg):
        # 'shorthelp' chosen arbitrarily: any mandatory field with a consistent
        # type would work.
        return 'shorthelp' in cfg and isinstance(cfg['shorthelp'], str)

    @staticmethod
    def __is_list(field, type):
        if field in ('filehash', 'date', 'author', 'example', 'enum', 'switch', 'package'):
            return True

        is_list = type.startswith('[')
        if is_list and field in ('signature', 'value'):
            return True

        return False

    @staticmethod
    def __validate_step_index(pernode, field, step, index):
        '''Shared validation logic for the step and index keyword arguments to
        get(), set(), and add(), based on the pernode setting of a parameter and
        field.

        Returns an error message if there's a problem with the arguments,
        otherwise None.
        '''
        if field not in Schema.PERNODE_FIELDS:
            if step is not None or index is not None:
                return 'step and index are only valid for value fields'
            return None

        if pernode == 'never' and (step is not None or index is not None):
            return 'step and index are not valid for this parameter'

        if pernode == 'required' and (step is None or index is None):
            return 'step and index are required for this parameter'

        if step is None and index is not None:
            return 'if index is provided, step must be provided as well'

        # Step and index for default should be accessed set_/get_default
        if step == 'default':
            return f'illegal step name: {step} is reserved'

        if index == 'default':
            return f'illegal index name: {step} is reserved'

        return None

    def __search(self, *keypath, insert_defaults=False, job=None):
        if job is not None:
            cfg = self.cfg['history'][job]
        else:
            cfg = self.cfg

        for key in keypath:
            if not isinstance(key, str):
                raise TypeError(f'Invalid keypath {keypath}: key is not a string: {key}')

            if Schema._is_leaf(cfg):
                raise ValueError(f'Invalid keypath {keypath}: unexpected key: {key}')

            if key in cfg:
                cfg = cfg[key]
            elif 'default' in cfg:
                if insert_defaults:
                    cfg[key] = copy.deepcopy(cfg['default'])
                    cfg = cfg[key]
                else:
                    cfg = cfg['default']
            else:
                raise ValueError(f'Invalid keypath {keypath}: unexpected key: {key}')

        return cfg

    ###########################################################################
    def allkeys(self, *keypath_prefix):
        '''
        Returns all keypaths in the schema as a list of lists.

        See :meth:`~siliconcompiler.core.Chip.allkeys` for detailed documentation.
        '''
        if len(keypath_prefix) > 0:
            return self.__allkeys(cfg=self.getdict(*keypath_prefix))
        else:
            return self.__allkeys()

    ###########################################################################
    def __allkeys(self, cfg=None, base_key=None):
        if cfg is None:
            cfg = self.cfg

        if Schema._is_leaf(cfg):
            return []

        keylist = []
        if base_key is None:
            base_key = []
        for k in cfg:
            key = (*base_key, k)
            if Schema._is_leaf(cfg[k]):
                keylist.append(key)
            else:
                keylist.extend(self.__allkeys(cfg=cfg[k], base_key=key))
        return keylist

    ###########################################################################
    def __copyparam(self, cfgsrc, cfgdst, keypath):
        '''
        Copies a parameter into the manifest history dictionary.
        '''

        # 1. descend keypath, pop each key as its used
        # 2. create key if missing in destination dict
        # 3. populate leaf cell when keypath empty
        if keypath:
            keypath = list(keypath)
            key = keypath[0]
            keypath.pop(0)
            if key not in cfgdst.keys():
                cfgdst[key] = {}
            self.__copyparam(cfgsrc[key], cfgdst[key], keypath)
        else:
            for key in cfgsrc.keys():
                if key not in ('example', 'switch', 'help'):
                    cfgdst[key] = copy.deepcopy(cfgsrc[key])

    ###########################################################################
    def write_json(self, fout):
        localcfg = self.copy().cfg
        if self.__journal is not None:
            localcfg['__journal__'] = self.__journal
        fout.write(json.dumps(localcfg, indent=4))

    ###########################################################################
    def write_yaml(self, fout):
        if not _has_yaml:
            raise ImportError('yaml package required to write YAML manifest')
        fout.write(yaml.dump(self.cfg, Dumper=YamlIndentDumper, default_flow_style=False))

    ###########################################################################
    def write_tcl(self, fout, prefix="", step=None, index=None, template=None):
        '''
        Prints out schema as TCL dictionary
        '''

        tcl_set_cmds = []
        for key in self.allkeys():
            typestr = self.get(*key, field='type')
            pernode = self.get(*key, field='pernode')

            if pernode == 'required' and (step is None or index is None):
                # Skip mandatory per-node parameters if step and index are not specified
                # TODO: how should we dump these?
                continue

            if pernode != 'never':
                value = self.get(*key, step=step, index=index)
            else:
                value = self.get(*key)

            # create a TCL dict
            keystr = ' '.join([escape_val_tcl(keypart, 'str') for keypart in key])

            valstr = escape_val_tcl(value, typestr)

            # Turning scalars into lists
            if not (typestr.startswith('[') or typestr.startswith('(')):
                valstr = f'[list {valstr}]'

            # TODO: Temp fix to get rid of empty args
            if valstr == '':
                valstr = '[list ]'

            outstr = f"{prefix} {keystr} {valstr}"

            # print out all non default values
            if 'default' not in key:
                tcl_set_cmds.append(outstr)

        if template:
            fout.write(template.render(manifest_dict='\n'.join(tcl_set_cmds),
                                       scroot=os.path.abspath(PACKAGE_ROOT)))
        else:
            for cmd in tcl_set_cmds:
                fout.write(cmd + '\n')
            fout.write('\n')

    ###########################################################################
    def write_csv(self, fout):
        csvwriter = csv.writer(fout)
        csvwriter.writerow(['Keypath', 'Value'])

        allkeys = self.allkeys()
        for key in allkeys:
            keypath = ','.join(key)
            for value, step, index in self._getvals(*key):
                if step is None and index is None:
                    keypath = ','.join(key)
                elif index is None:
                    keypath = ','.join([*key, step, 'default'])
                else:
                    keypath = ','.join([*key, step, index])

                if isinstance(value, list):
                    for item in value:
                        csvwriter.writerow([keypath, item])
                else:
                    csvwriter.writerow([keypath, value])

    ###########################################################################
    def copy(self):
        '''Returns deep copy of Schema object.'''
        newscheme = Schema(cfg=self.cfg)
        if self.__journal:
            newscheme.__journal = copy.deepcopy(self.__journal)
        return newscheme

    ###########################################################################
    def prune(self):
        '''Remove all empty parameters from configuration dictionary.

        Also deletes 'help' and 'example' keys.
        '''
        # When at top of tree loop maxdepth times to make sure all stale
        # branches have been removed, not elegant, but stupid-simple
        # "good enough"

        # 10 should be enough for anyone...
        maxdepth = 10

        for _ in range(maxdepth):
            self.__prune()

    ###########################################################################
    def __prune(self, *keypath):
        '''
        Internal recursive function that creates a local copy of the Chip
        schema (cfg) with only essential non-empty parameters retained.

        '''
        cfg = self.__search(*keypath)

        # Prune when the default & value are set to the following
        # Loop through all keys starting at the top
        for k in list(cfg.keys()):
            # removing all default/template keys
            # reached a default subgraph, delete it
            if k == 'default':
                del cfg[k]
            # reached leaf-cell
            elif 'help' in cfg[k].keys():
                del cfg[k]['help']
            elif 'example' in cfg[k].keys():
                del cfg[k]['example']
            elif Schema._is_leaf(cfg[k]):
                pass
            # removing stale branches
            elif not cfg[k]:
                cfg.pop(k)
            # keep traversing tree
            else:
                self.__prune(*keypath, k)

    ###########################################################################
    def is_empty(self, *keypath):
        '''
        Utility function to check key for an empty value.
        '''
        empty = (None, [])

        values = self._getvals(*keypath)
        defvalue = self.get_default(*keypath)
        value_empty = (defvalue in empty) and \
            all([value in empty for value, _, _ in values])
        return value_empty

    ###########################################################################
    def history(self, job):
        '''
        Returns a *mutable* reference to ['history', job] as a Schema object.

        If job doesn't currently exist in history, create it with default
        values.

        Args:
            job (str): Name of historical job to return.
        '''
        if job not in self.cfg['history']:
            self.cfg['history'][job] = self._init_schema_cfg()

        # Can't initialize Schema() by passing in cfg since it performs a deep
        # copy.
        schema = Schema()
        schema.cfg = self.cfg['history'][job]
        return schema

    #######################################
    def _init_logger(self, parent=None):
        if parent:
            # If parent provided, create a child logger
            self.logger = parent.getChild('schema')
        else:
            # Check if the logger exists and create
            if not hasattr(self, 'logger') or not self.logger:
                self.logger = logging.getLogger(f'sc_schema_{id(self)}')
                self.logger.propagate = False

    #######################################
    def __getstate__(self):
        attributes = self.__dict__.copy()

        # We have to remove the chip's logger before serializing the object
        # since the logger object is not serializable.
        del attributes['logger']
        return attributes

    #######################################
    def __setstate__(self, state):
        self.__dict__ = state

        # Reinitialize logger on restore
        self._init_logger()

    #######################################
    def __record_journal(self, record_type, key, value=None, field=None, step=None, index=None):
        '''
        Record the schema transaction
        '''
        if self.__journal is None:
            return

        self.__journal.append({
            "type": record_type,
            "key": key,
            "value": value,
            "field": field,
            "step": step,
            "index": index
        })

    #######################################
    def _start_journal(self):
        '''
        Start journaling the schema transactions
        '''
        self.__journal = []

    #######################################
    def _stop_journal(self):
        '''
        Stop journaling the schema transactions
        '''
        self.__journal = None

    #######################################
    def read_journal(self, filename):
        '''
        Reads a manifest and replays the journal
        '''

        schema = Schema(manifest=filename, logger=self.logger)
        self._import_journal(schema)

    #######################################
    def _import_journal(self, schema):
        '''
        Import the journaled transactions from a different schema
        '''
        if not schema.__journal:
            return

        for action in schema.__journal:
            record_type = action['type']
            keypath = action['key']
            value = action['value']
            field = action['field']
            step = action['step']
            index = action['index']
            try:
                if record_type == 'set':
                    cfg = self.__search(*keypath, insert_defaults=True)
                    self.__set(*keypath, value, logger=self.logger, cfg=cfg, field=field,
                               step=step, index=index, journal_callback=None)
                elif record_type == 'add':
                    cfg = self.__search(*keypath, insert_defaults=True)
                    self._add(*keypath, value, cfg=cfg, field=field, step=step, index=index)
                elif record_type == 'unset':
                    self.unset(*keypath, step=step, index=index)
                elif record_type == 'remove':
                    self.remove(*keypath)
                else:
                    raise ValueError(f'Unknown record type {record_type}')
            except Exception as e:
                self.logger.error(f'Exception: {e}')

    #######################################
    def get_default(self, *keypath):
        '''Returns default value of a parameter.

        Args:
            keypath(list str): Variable length schema key list.
        '''
        cfg = self.__search(*keypath)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: get_default() '
                             'must be called on a complete keypath')

        return cfg['node']['default']['default']['value']

    #######################################
    def set_default(self, *args):
        '''Sets the default value of a parameter.

        Args:
            args (list str): Variable length schema key list and value.
        '''
        keypath = args[:-1]
        value = args[-1]
        cfg = self.__search(*keypath)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: set_default() '
                             'must be called on a complete keypath')

        allowed_values = None
        if 'enum' in cfg:
            allowed_values = cfg['enum']

        cfg['node']['default']['default']['value'] = Schema.__check_and_normalize(
            value, cfg['type'], 'value', keypath, allowed_values)

    ###########################################################################
    def create_cmdline(self,
                       progname,
                       description=None,
                       switchlist=None,
                       input_map=None,
                       additional_args=None,
                       version=None,
                       print_banner=None,
                       input_map_handler=None,
                       preprocess_keys=None,
                       post_process=None,
                       logger=None):
        """Creates a Schema command line interface.

        Exposes parameters in the SC schema as command line switches,
        simplifying creation of SC apps with a restricted set of schema
        parameters exposed at the command line. The order of command
        line switch settings parsed from the command line is as follows:

         1. loglevel, if available in schema
         2. read_manifest([cfg]), if available in schema
         3. read inputs with input_map_handler
         4. all other switches
         5. Run post_process

        The cmdline interface is implemented using the Python argparse package
        and the following use restrictions apply.

        * Help is accessed with the '-h' switch.
        * Arguments that include spaces must be enclosed with double quotes.
        * List parameters are entered individually. (ie. -y libdir1 -y libdir2)
        * For parameters with Boolean types, the switch implies "true".
        * Special characters (such as '-') must be enclosed in double quotes.
        * Compiler compatible switches include: -D, -I, -O{0,1,2,3}
        * Legacy switch formats are supported: +libext+, +incdir+

        Args:
            progname (str): Name of program to be executed.
            description (str): Short program description.
            switchlist (list of str): List of SC parameter switches to expose
                at the command line. By default all SC schema switches are
                available. Parameter switches should be entered based on the
                parameter 'switch' field in the schema. For parameters with
                multiple switches, both will be accepted if any one is included
                in this list.
            input_map (dict of str): Dictionary mapping file extensions to input
                filetypes. This is used to automatically assign positional
                source arguments to ['input', 'fileset', ...] keypaths based on their file
                extension. If None, the CLI will not accept positional source
                arguments.
            additional_args (dict of dict): Dictionary of extra arguments to add
                to the command line parser, with the arguments matching the
                argparse.add_argument() call.
            version (str): Version to report when calling with -version
            print_banner (function): Function callback to print command line banner
            input_map_handler (function): Function callback handle inputs to the input map
            preprocess_keys (function): Function callback to preprocess keys that need to be
                corrected
            post_process (function): Function callback to process arguments before returning

        Returns:
            None if additional_args is not provided, otherwise a dictionary with the
                command line options detected from the additional_args

        Examples:
            >>> schema.create_cmdline(progname='sc-show',switchlist=['-input','-cfg'])
            Creates a command line interface for 'sc-show' app.
            >>> schema.create_cmdline(progname='sc', input_map={'v': ('rtl', 'verilog')})
            All sources ending in .v will be stored in ['input', 'rtl', 'verilog']
            >>> extra = schema.create_cmdline(progname='sc',
                                              additional_args={'-demo': {'action': 'store_true'}})
            Returns extra = {'demo': False/True}
        """

        if not logger:
            logger = self.logger

        # Argparse
        parser = argparse.ArgumentParser(prog=progname,
                                         prefix_chars='-+',
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description=description,
                                         allow_abbrev=False)

        # Get a new schema, in case values have already been set
        schema_class = type(self)
        schema = schema_class(logger=self.logger)

        # Iterate over all keys from an empty schema to add parser arguments
        used_switches = set()
        for keypath in schema.allkeys():
            # Fetch fields from leaf cell
            helpstr = schema.get(*keypath, field='shorthelp')
            typestr = schema.get(*keypath, field='type')
            pernodestr = schema.get(*keypath, field='pernode')

            # argparse 'dest' must be a string, so join keypath with commas
            dest = '_'.join(keypath)

            switchstrs, metavar = self.__get_switches(schema, *keypath)

            # Three switch types (bool, list, scalar)
            if not switchlist or any(switch in switchlist for switch in switchstrs):
                used_switches.update(switchstrs)
                if typestr == 'bool':
                    # Boolean type arguments
                    if pernodestr == 'never':
                        parser.add_argument(*switchstrs,
                                            nargs='?',
                                            metavar=metavar,
                                            dest=dest,
                                            const='true',
                                            help=helpstr,
                                            default=argparse.SUPPRESS)
                    else:
                        parser.add_argument(*switchstrs,
                                            metavar=metavar,
                                            nargs='?',
                                            dest=dest,
                                            action='append',
                                            help=helpstr,
                                            default=argparse.SUPPRESS)
                elif re.match(r'\[', typestr) or pernodestr != 'never':
                    # list type arguments
                    parser.add_argument(*switchstrs,
                                        metavar=metavar,
                                        dest=dest,
                                        action='append',
                                        help=helpstr,
                                        default=argparse.SUPPRESS)
                else:
                    # all the rest
                    parser.add_argument(*switchstrs,
                                        metavar=metavar,
                                        dest=dest,
                                        help=helpstr,
                                        default=argparse.SUPPRESS)

        # Check if there are invalid switches
        if switchlist:
            for switch in switchlist:
                if switch not in used_switches:
                    raise ValueError(f'{switch} is not a valid commandline argument')

        if input_map is not None and input_map_handler:
            parser.add_argument('source',
                                nargs='*',
                                help='Input files with filetype inferred by extension')

        # Preprocess sys.argv to enable linux commandline switch formats
        # (gcc, verilator, etc)
        scargs = []

        # Iterate from index 1, otherwise we end up with script name as a
        # 'source' positional argument
        for argument in sys.argv[1:]:
            # Split switches with one character and a number after (O0,O1,O2)
            opt = re.match(r'(\-\w)(\d+)', argument)
            # Split assign switches (-DCFG_ASIC=1)
            assign = re.search(r'(\-\w)(\w+\=\w+)', argument)
            # Split plusargs (+incdir+/path)
            plusarg = re.search(r'(\+\w+\+)(.*)', argument)
            if opt:
                scargs.append(opt.group(1))
                scargs.append(opt.group(2))
            elif plusarg:
                scargs.append(plusarg.group(1))
                scargs.append(plusarg.group(2))
            elif assign:
                scargs.append(assign.group(1))
                scargs.append(assign.group(2))
            else:
                scargs.append(argument)

        if version:
            parser.add_argument('-version', action='version', version=version)

        print_additional_arg_value = {}
        if additional_args:
            # Add additional user specified arguments
            arg_dests = []
            for arg, arg_detail in additional_args.items():
                do_print = True
                if "sc_print" in arg_detail:
                    do_print = arg_detail["sc_print"]
                    del arg_detail["sc_print"]
                argument = parser.add_argument(arg, **arg_detail)
                print_additional_arg_value[argument.dest] = do_print

                arg_dests.append(argument.dest)
            # rewrite additional_args with new dest information
            additional_args = arg_dests

        # Grab argument from pre-process sysargs
        cmdargs = vars(parser.parse_args(scargs))

        if print_banner:
            print_banner()

        extra_params = None
        if additional_args:
            # Grab user specified arguments
            extra_params = {}
            for arg in additional_args:
                if arg in cmdargs:
                    val = cmdargs[arg]
                    if print_additional_arg_value[arg]:
                        msg = f'Command line argument entered: "{arg}" Value: {val}'
                        self.logger.info(msg)
                    extra_params[arg] = val
                    # Remove from cmdargs
                    del cmdargs[arg]

        # Set loglevel if set at command line
        if 'option_loglevel' in cmdargs.keys():
            log_level = cmdargs['option_loglevel']
            if isinstance(log_level, list):
                # if multiple found, pick the first one
                log_level = log_level[0]
            logger.setLevel(translate_loglevel(log_level).split()[-1])

        # Read in all cfg files
        if 'option_cfg' in cmdargs.keys():
            for item in cmdargs['option_cfg']:
                self.read_manifest(item, clobber=True, clear=True, allow_missing_keys=True)

        if input_map_handler:
            # Map sources to ['input'] keypath.
            if 'source' in cmdargs:
                input_map_handler(cmdargs['source'])
                # we don't want to handle this in the next loop
                del cmdargs['source']

        # Cycle through all command args and write to manifest
        for dest, vals in cmdargs.items():
            keypath = dest.split('_')

            # Turn everything into a list for uniformity
            if not isinstance(vals, list):
                vals = [vals]

            # Cycle through all items
            for item in vals:
                if item is None:
                    # nargs=? leaves a None for booleans
                    item = ''

                if preprocess_keys:
                    item = preprocess_keys(keypath, item)

                num_free_keys = keypath.count('default')

                switches, metavar = self.__get_switches(schema, *keypath)
                switchstr = '/'.join(switches)

                if len(item.split(' ')) < num_free_keys + 1:
                    # Error out if value provided doesn't have enough words to
                    # fill in 'default' keys.
                    raise ValueError(f'Invalid value {item} for switch {switchstr}. '
                                     f'Expected format {metavar}.')

                # We replace 'default' in keypath with first N words in provided
                # value.
                *free_keys, remainder = item.split(' ', num_free_keys)
                args = [free_keys.pop(0) if key == 'default' else key for key in keypath]

                # Remainder is the value we want to set, possibly with a step/index value beforehand
                sctype = self.get(*keypath, field='type')
                pernode = self.get(*keypath, field='pernode')
                step, index = None, None
                if pernode == 'required':
                    try:
                        step, index, val = remainder.split(' ', 2)
                    except ValueError:
                        self.logger.error(f"Invalid value '{item}' for switch {switchstr}. "
                                          "Requires step and index before final value.")
                elif pernode == 'optional':
                    # Split on spaces, preserving items that are grouped in quotes
                    items = shlex.split(remainder)
                    if len(items) > 3:
                        self.logger.error(f"Invalid value '{item}'' for switch {switchstr}. "
                                          "Too many arguments, please wrap multiline "
                                          "strings in quotes.")
                        continue
                    if sctype == 'bool':
                        if len(items) == 3:
                            step, index, val = items
                        elif len(items) == 2:
                            step, val = items
                            if val != 'true' and val != 'false':
                                index = val
                                val = True
                        elif len(items) == 1:
                            val, = items
                            if val != 'true' and val != 'false':
                                step = val
                                val = True
                        else:
                            val = True
                    else:
                        if len(items) == 3:
                            step, index, val = items
                        elif len(items) == 2:
                            step, val = items
                        else:
                            val, = items
                else:
                    val = remainder

                msg = f'Command line argument entered: {args} Value: {val}'
                if step is not None:
                    msg += f' Step: {step}'
                if index is not None:
                    msg += f' Index: {index}'
                self.logger.info(msg)

                # Storing in manifest
                typestr = schema.get(*keypath, field='type')
                if typestr.startswith('['):
                    if self.valid(*args):
                        self.add(*args, val, step=step, index=index)
                    else:
                        self.set(*args, val, step=step, index=index, clobber=True)
                else:
                    self.set(*args, val, step=step, index=index, clobber=True)

        if post_process:
            post_process(cmdargs)

        return extra_params

    ###########################################################################
    def __get_switches(self, schema, *keypath):
        '''Helper function for parsing switches and metavars for a keypath.'''
        # Switch field fully describes switch format
        switch = schema.get(*keypath, field='switch')

        if switch is None:
            switches = []
        elif isinstance(switch, list):
            switches = switch
        else:
            switches = [switch]
        switchstrs = []

        # parse out switch from metavar
        # TODO: should we validate that metavar matches for each switch?
        for switch in switches:
            switchmatch = re.match(r'(-[\w_]+)\s+(.*)', switch)
            gccmatch = re.match(r'(-[\w_]+)(.*)', switch)
            plusmatch = re.match(r'(\+[\w_\+]+)(.*)', switch)

            if switchmatch:
                switchstr = switchmatch.group(1)
                metavar = switchmatch.group(2)
            elif gccmatch:
                switchstr = gccmatch.group(1)
                metavar = gccmatch.group(2)
            elif plusmatch:
                switchstr = plusmatch.group(1)
                metavar = plusmatch.group(2)
            switchstrs.append(switchstr)

        return switchstrs, metavar

    ###########################################################################
    def read_manifest(self, filename, clear=True, clobber=True, allow_missing_keys=True):
        """
        Reads a manifest from disk and merges it with the current manifest.

        The file format read is determined by the filename suffix. Currently
        json (*.json) and yaml(*.yaml) formats are supported.

        Args:
            filename (filepath): Path to a manifest file to be loaded.
            clear (bool): If True, disables append operations for list type.
            clobber (bool): If True, overwrites existing parameter value.
            allow_missing_keys (bool): If True, keys not present in current schema will be ignored.

        Examples:
            >>> chip.read_manifest('mychip.json')
            Loads the file mychip.json into the current Chip object.
        """
        schema = Schema(manifest=filename, logger=self.logger)

        if schema.get('schemaversion') != self.get('schemaversion'):
            self.logger.warning("Mismatch in schema versions: "
                                f"{schema.get('schemaversion')} != {self.get('schemaversion')}")

        for keylist in schema.allkeys():
            if keylist[0] in ('history', 'library'):
                continue
            if 'default' in keylist:
                continue
            typestr = schema.get(*keylist, field='type')
            should_append = re.match(r'\[', typestr) and not clear

            if allow_missing_keys and not self.valid(*keylist, default_valid=True):
                self.logger.warning(f'{keylist} not found in schema, skipping...')
                continue

            for val, step, index in schema._getvals(*keylist, return_defvalue=False):
                # update value, handling scalars vs. lists
                if should_append:
                    self.add(*keylist, val, step=step, index=index)
                else:
                    self.set(*keylist, val, step=step, index=index, clobber=clobber)

                # update other pernode fields
                # TODO: only update these if clobber is successful
                step_key = Schema.GLOBAL_KEY if not step else step
                idx_key = Schema.GLOBAL_KEY if not index else index
                for field in schema.getdict(*keylist)['node'][step_key][idx_key].keys():
                    if field == 'value':
                        continue
                    v = schema.get(*keylist, step=step, index=index, field=field)
                    if should_append:
                        self.add(*keylist, v, step=step, index=index, field=field)
                    else:
                        self.set(*keylist, v, step=step, index=index, field=field)

            # update other fields that a user might modify
            for field in schema.getdict(*keylist).keys():
                if field in ('node',):
                    # skip these fields (node handled above)
                    continue

                # TODO: should we be taking into consideration clobber for these fields?
                v = schema.get(*keylist, field=field)
                self.set(*keylist, v, field=field)

        # Read history, if we're not already reading into a job
        if 'history' in schema.getkeys():
            for historic_job in schema.getkeys('history'):
                self.cfg['history'][historic_job] = schema.getdict('history', historic_job)

        # TODO: better way to handle this?
        if 'library' in schema.getkeys():
            for libname in schema.getkeys('library'):
                self.cfg['library'][libname] = schema.getdict('library', libname)

    ###########################################################################
    def merge_manifest(self, src, job=None, clobber=True, clear=True, check=False):
        """
        Merges a given manifest with the current compilation manifest.

        All value fields in the provided schema dictionary are merged into the
        current chip object. Dictionaries with non-existent keypath produces a
        logger error message and raises the Chip object error flag.

        Args:
            src (Schema): Schema object to merge
            job (str): Specifies non-default job to merge into
            clear (bool): If True, disables append operations for list type
            clobber (bool): If True, overwrites existing parameter value
            check (bool): If True, checks the validity of each key
        """
        if job is not None:
            dest = self.history(job)
        else:
            dest = self

        for keylist in src.allkeys():
            if keylist[0] in ('history', 'library'):
                continue
            # only read in valid keypaths without 'default'
            key_valid = True
            if check:
                key_valid = dest.valid(*keylist, default_valid=True)
                if not key_valid:
                    self.logger.warning(f'Keypath {keylist} is not valid')
            if key_valid and 'default' not in keylist:
                typestr = src.get(*keylist, field='type')
                should_append = re.match(r'\[', typestr) and not clear
                key_cfg = src.__search(*keylist)
                for val, step, index in src._getvals(*keylist, return_defvalue=False):
                    # update value, handling scalars vs. lists
                    if should_append:
                        dest.add(*keylist, val, step=step, index=index)
                    else:
                        dest.set(*keylist, val, step=step, index=index, clobber=clobber)

                    # update other pernode fields
                    # TODO: only update these if clobber is successful
                    step_key = Schema.GLOBAL_KEY if not step else step
                    idx_key = Schema.GLOBAL_KEY if not index else index
                    for field in key_cfg['node'][step_key][idx_key].keys():
                        if field == 'value':
                            continue
                        v = src.get(*keylist, step=step, index=index, field=field)
                        if should_append:
                            dest.add(*keylist, v, step=step, index=index, field=field)
                        else:
                            dest.set(*keylist, v, step=step, index=index, field=field)

                # update other fields that a user might modify
                for field in key_cfg.keys():
                    if field in ('node', 'switch', 'type', 'require',
                                 'shorthelp', 'example', 'help'):
                        # skip these fields (node handled above, others are static)
                        continue
                    # TODO: should we be taking into consideration clobber for these fields?
                    v = src.get(*keylist, field=field)
                    dest.set(*keylist, v, field=field)


if _has_yaml:
    class YamlIndentDumper(yaml.Dumper):
        def increase_indent(self, flow=False, indentless=False):
            return super(YamlIndentDumper, self).increase_indent(flow, False)
