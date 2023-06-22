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

try:
    import yaml
    _has_yaml = True
except ImportError:
    _has_yaml = False

from .schema_cfg import schema_cfg
from .utils import escape_val_tcl, PACKAGE_ROOT


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

    # Special key in node dict that represents a value correponds to a
    # global default for all steps/indices.
    GLOBAL_KEY = 'global'
    PERNODE_FIELDS = ('value', 'filehash', 'date', 'author', 'signature')

    def __init__(self, cfg=None, manifest=None, logger=None):
        if cfg is not None and manifest is not None:
            raise ValueError('You may not specify both cfg and manifest')

        self._init_logger(logger)

        if cfg is not None:
            self.cfg = Schema._dict_to_schema(copy.deepcopy(cfg))
        elif manifest is not None:
            # Normalize value to string in case we receive a pathlib.Path
            manifest = str(manifest)
            self.cfg = Schema._read_manifest(manifest)
        else:
            self.cfg = schema_cfg()

    ###########################################################################
    @staticmethod
    def _dict_to_schema_set(cfg, *key):
        if Schema._is_leaf(cfg):
            for field, value in cfg.items():
                if field == 'node':
                    for step in value:
                        if step == 'default':
                            continue
                        for index in value[step]:
                            if step == Schema.GLOBAL_KEY:
                                sstep = None
                            else:
                                sstep = step
                            if index == Schema.GLOBAL_KEY:
                                sindex = None
                            else:
                                sindex = index
                            for nodefield, nodevalue in value[step][index].items():
                                Schema._set(*key, nodevalue,
                                            cfg=cfg,
                                            field=nodefield,
                                            step=sstep, index=sindex)
                else:
                    Schema._set(*key, value, cfg=cfg, field=field)
        else:
            for nextkey in cfg.keys():
                Schema._dict_to_schema_set(cfg[nextkey], *key, nextkey)

    ###########################################################################
    @staticmethod
    def _dict_to_schema(cfg):
        for category in cfg.keys():
            if category in ('history', 'library'):
                # History and library are subschemas
                for _, value in cfg[category].items():
                    Schema._dict_to_schema(value)
            else:
                Schema._dict_to_schema_set(cfg[category], category)
        return cfg

    ###########################################################################
    @staticmethod
    def _read_manifest(filepath):
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

        try:
            Schema._dict_to_schema(localcfg)
        except (TypeError, ValueError) as e:
            raise ValueError(f'Attempting to read manifest with incompatible schema version: {e}') \
                from e

        return localcfg

    ###########################################################################
    def get(self, *keypath, field='value', job=None, step=None, index=None):
        """
        Returns a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.get` for detailed documentation.
        """
        cfg = self._search(*keypath, job=job)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: get() '
                             'must be called on a complete keypath')

        err = Schema._validate_step_index(cfg['pernode'], field, step, index)
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
        cfg = self._search(*keypath, insert_defaults=True)

        return self._set(*args, logger=self.logger, cfg=cfg, field=field, clobber=clobber,
                         step=step, index=index)

    ###########################################################################
    @staticmethod
    def _set(*args, logger=None, cfg=None, field='value', clobber=True, step=None, index=None):
        '''
        Sets a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.set` for detailed documentation.
        '''
        keypath = args[:-1]
        value = args[-1]

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: set() '
                             'must be called on a complete keypath')

        err = Schema._validate_step_index(cfg['pernode'], field, step, index)
        if err:
            raise ValueError(f'Invalid args to set() of keypath {keypath}: {err}')

        if isinstance(index, int):
            index = str(index)

        if cfg['lock']:
            if logger:
                logger.debug(f'Failed to set value for {keypath}: parameter is locked')
            return False

        if Schema._is_set(cfg, step=step, index=index) and not clobber:
            if logger:
                logger.debug(f'Failed to set value for {keypath}: clobber is False '
                             'and parameter is set')
            return False

        allowed_values = None
        if 'enum' in cfg:
            allowed_values = cfg['enum']

        value = Schema._check_and_normalize(value, cfg['type'], field, keypath, allowed_values)

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
        value = args[-1]

        cfg = self._search(*keypath, insert_defaults=True)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: add() '
                             'must be called on a complete keypath')

        err = Schema._validate_step_index(cfg['pernode'], field, step, index)
        if err:
            raise ValueError(f'Invalid args to add() of keypath {keypath}: {err}')

        if isinstance(index, int):
            index = str(index)

        if not Schema._is_list(field, cfg['type']):
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

        value = Schema._check_and_normalize(value, cfg['type'], field, keypath, allowed_values)
        if field in self.PERNODE_FIELDS:
            step = step if step is not None else self.GLOBAL_KEY
            index = index if index is not None else self.GLOBAL_KEY

            if step not in cfg['node']:
                cfg['node'][step] = {}
            if index not in cfg['node'][step]:
                cfg['node'][step][index] = copy.deepcopy(cfg['node']['default']['default'])
            cfg['node'][step][index][field].extend(value)
        else:
            cfg[field].extend(value)

        return True

    ###########################################################################
    def unset(self, *keypath, step=None, index=None):
        '''
        Unsets a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.unset` for detailed documentation.
        '''
        cfg = self._search(*keypath)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: unset() '
                             'must be called on a complete keypath')

        err = Schema._validate_step_index(cfg['pernode'], 'value', step, index)
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
        cfg = self._search(*keypath)

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
        cfg = self._search(*keypath, job=job)
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
        cfg = self._search(*keypath)
        return copy.deepcopy(cfg)

    ###########################################################################
    def valid(self, *args, valid_keypaths=None, default_valid=False):
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

        if valid_keypaths is None:
            valid_keypaths = self.allkeys()

        # Look for a full match with default playing wild card
        for valid_keypath in valid_keypaths:
            if len(keylist) != len(valid_keypath):
                continue

            ok = True
            for i in range(len(keylist)):
                if valid_keypath[i] not in (keylist[i], default):
                    ok = False
                    break
            if ok:
                return True

        return False

    ##########################################################################
    def _has_field(self, *args):
        keypath = args[:-1]
        field = args[-1]

        cfg = self._search(*keypath)
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
                if not self._is_empty(*key) and (scope == 'job'):
                    self._copyparam(self.cfg,
                                    self.cfg['history'][jobname],
                                    key)

    @staticmethod
    def _check_and_normalize(value, sc_type, field, keypath, allowed_values):
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

        if value is None and not Schema._is_list(field, sc_type):
            # None is legal for all scalars, but not within collection types
            # TODO: could consider normalizing "None" for lists to empty list?
            return value

        if field == 'value':
            # Push down error_msg from the top since arguments get modified in recursive call
            error_msg = f'Invalid value {value} for keypath {keypath}: expected type {sc_type}'
            return Schema._normalize_value(value, sc_type, error_msg, allowed_values)
        else:
            return Schema._normalize_field(value, sc_type, field, keypath)

    @staticmethod
    def _normalize_value(value, sc_type, error_msg, allowed_values):
        if sc_type.startswith('['):
            if not isinstance(value, list):
                value = [value]
            base_type = sc_type[1:-1]
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
            else:
                raise TypeError(error_msg)

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
    def _normalize_field(value, sc_type, field, keypath):
        def error_msg(t):
            return f'Invalid value {value} for field {field} of keypath {keypath}: expected {t}'

        if field in ('author', 'filehash', 'date', 'hashalgo') and ('file' not in sc_type):
            raise TypeError(f'Invalid field {field} for keypath {keypath}: '
                            'this field only exists for file parameters')

        if field in ('copy',) and ('file' not in sc_type and 'dir' not in sc_type):
            raise TypeError(f'Invalid field {field} for keypath {keypath}: '
                            'this field only exists for file and dir parameters')

        if Schema._is_list(field, sc_type):
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
            'signature', 'require'
        ):
            if not isinstance(value, str):
                raise TypeError(error_msg('str'))
            return value

        if field in ('lock', 'copy'):
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
    def _is_set(cfg, step=None, index=None):
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
    def _is_list(field, type):
        is_list = type.startswith('[')

        if field in ('filehash', 'date', 'author', 'example', 'enum', 'switch'):
            return True

        if is_list and field in ('signature', 'value'):
            return True

        return False

    @staticmethod
    def _validate_step_index(pernode, field, step, index):
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

        if step in (Schema.GLOBAL_KEY, 'default'):
            return f'illegal step name: {step} is reserved'

        if index in (Schema.GLOBAL_KEY, 'default'):
            return f'illegal index name: {step} is reserved'

        return None

    def _search(self, *keypath, insert_defaults=False, job=None):
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
            return self._allkeys(self.getdict(*keypath_prefix))
        else:
            return self._allkeys()

    ###########################################################################
    def _allkeys(self, cfg=None, keys=None, keylist=None):
        if cfg is None:
            cfg = self.cfg

        if keys is None:
            keylist = []
            keys = []
        for k in cfg:
            newkeys = keys.copy()
            newkeys.append(k)
            if Schema._is_leaf(cfg[k]):
                keylist.append(newkeys)
            else:
                self._allkeys(cfg=cfg[k], keys=newkeys, keylist=keylist)
        return keylist

    ###########################################################################
    def _copyparam(self, cfgsrc, cfgdst, keypath):
        '''
        Copies a parameter into the manifest history dictionary.
        '''

        # 1. descend keypath, pop each key as its used
        # 2. create key if missing in destination dict
        # 3. populate leaf cell when keypath empty
        if keypath:
            key = keypath[0]
            keypath.pop(0)
            if key not in cfgdst.keys():
                cfgdst[key] = {}
            self._copyparam(cfgsrc[key], cfgdst[key], keypath)
        else:
            for key in cfgsrc.keys():
                if key not in ('example', 'switch', 'help'):
                    cfgdst[key] = copy.deepcopy(cfgsrc[key])

    ###########################################################################
    def write_json(self, fout):
        fout.write(json.dumps(self.cfg, indent=4, sort_keys=True))

    ###########################################################################
    def write_yaml(self, fout):
        if not _has_yaml:
            raise ImportError('yaml package required to write YAML manifest')
        fout.write(yaml.dump(self.cfg, Dumper=YamlIndentDumper, default_flow_style=False))

    ###########################################################################
    def write_tcl(self, fout, prefix="", step=None, index=None):
        '''
        Prints out schema as TCL dictionary
        '''
        manifest_header = os.path.join(PACKAGE_ROOT, 'data', 'sc_manifest_header.tcl')
        with open(manifest_header, 'r') as f:
            fout.write(f.read())
        fout.write('\n')

        allkeys = self.allkeys()

        for key in allkeys:
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

            outstr = f"{prefix} {keystr} {valstr}\n"

            # print out all non default values
            if 'default' not in key:
                fout.write(outstr)

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
                    keypath = ','.join(key + [step, 'default'])
                else:
                    keypath = ','.join(key + [step, index])

                if isinstance(value, list):
                    for item in value:
                        csvwriter.writerow([keypath, item])
                else:
                    csvwriter.writerow([keypath, value])

    ###########################################################################
    def copy(self):
        '''Returns deep copy of Schema object.'''
        return Schema(cfg=self.cfg)

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
            self._prune()

    ###########################################################################
    def _prune(self, *keypath):
        '''
        Internal recursive function that creates a local copy of the Chip
        schema (cfg) with only essential non-empty parameters retained.

        '''
        cfg = self._search(*keypath)

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
                self._prune(*keypath, k)

    ###########################################################################
    def _is_empty(self, *keypath):
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
            self.cfg['history'][job] = schema_cfg()

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
    def get_default(self, *keypath):
        '''Returns default value of a parameter.

        Args:
            keypath(list str): Variable length schema key list.
        '''
        cfg = self._search(*keypath)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: get_default() '
                             'must be called on a complete keypath')

        return cfg['node']['default']['default']['value']


if _has_yaml:
    class YamlIndentDumper(yaml.Dumper):
        def increase_indent(self, flow=False, indentless=False):
            return super(YamlIndentDumper, self).increase_indent(flow, False)
