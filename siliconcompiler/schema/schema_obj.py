# Copyright 2022 Silicon Compiler Authors. All Rights Reserved.

import copy
import csv
import gzip
import json
import os
import re
import yaml

from siliconcompiler import utils
from .schema_cfg import schema_cfg

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
    """

    def __init__(self, cfg=None, manifest=None):
        if cfg is not None and manifest is not None:
            raise ValueError('You may not specify both cfg and manifest')

        if cfg is not None:
            self.cfg = copy.deepcopy(cfg)
        elif manifest is not None:
            self.cfg = Schema._read_manifest(manifest)
        else:
            self.cfg = schema_cfg()

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
                localcfg = yaml.load(fin, Loader=yaml.SafeLoader)
            else:
                raise ValueError(f'File format not recognized {filepath}')
        finally:
            fin.close()

        if Schema().get('schemaversion') != localcfg['schemaversion']['value']:
            raise ValueError('Attempting to read manifest with incompatible schema version')

        return localcfg

    ###########################################################################
    def get(self, *keypath, field='value', job=None, step=None, index=None):
        """
        Returns a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.get` for detailed documentation.
        """
        cfg = self._search(*keypath, job=job)

        if cfg['pernode'] == 'none' and (step is not None or index is not None):
            raise ValueError(f'step and index are not valid for keypath {keypath}')

        if cfg['pernode'] == 'mandatory' and (step is None or index is None):
            raise ValueError(f'step and index must be provided for keypath {keypath}')

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: get() must be called on a complete keypath')

        if field == 'value':
            if cfg['pernode'] == 'mandatory':
                try:
                    return cfg['pernode_value'][step][index]
                except KeyError:
                    raise ValueError(f'No value for keypath {keypath} for node {step}{index}')

            if step in cfg['pernode_value'] and index in cfg['pernode_value'][step]:
                return cfg['pernode_value'][step][index]
            elif step in cfg['pernode_value']:
                return cfg['pernode_value'][step]['default']
            elif not Schema._is_empty(cfg):
                return cfg['value']
            else:
                return cfg['defvalue']
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
        value = args[-1]

        cfg = self._search(*keypath, insert_defaults=True)

        if cfg['pernode'] == 'none' and (step is not None or index is not None):
            raise ValueError(f'step and index are not valid for keypath {keypath}')

        if cfg['pernode'] == 'mandatory' and (step is None or index is None):
            raise ValueError(f'step and index must be provided for keypath {keypath}')

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: set() must be called on a complete keypath')

        if cfg['lock']:
            # TODO: log here
            return False

        if not Schema._is_empty(cfg) and not clobber:
            # TODO: log here
            return False

        allowed_values = None
        if 'enum' in cfg:
            allowed_values = cfg['enum']

        value = Schema._check_and_normalize(value, cfg['type'], field, keypath, allowed_values)

        if field == 'value':
            if step is not None and index is not None:
                if step not in cfg['pernode_value']:
                    cfg['pernode_value'][step] = {}
                cfg['pernode_value'][step][index] = value
            elif step is not None:
                if step not in cfg['pernode_value']:
                    cfg['pernode_value'][step] = {}
                cfg['pernode_value'][step]['default'] = value
            else:
                cfg['value'] = value
            cfg['set'] = True
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

        if cfg['pernode'] == 'none' and (step is not None or index is not None):
            raise ValueError(f'step and index are not valid for keypath {keypath}')

        if cfg['pernode'] == 'mandatory' and (step is None or index is None):
            raise ValueError(f'step and index must be provided for keypath {keypath}')

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: add() must be called on a complete keypath')

        if not Schema._is_list(field, cfg['type']):
            raise ValueError(f'Invalid keypath {keypath}: add() must be called on a complete keypath')

        if cfg['lock']:
            # TODO: log here
            return False

        allowed_values = None
        if 'enum' in cfg:
            allowed_values = cfg['enum']

        value = Schema._check_and_normalize(value, cfg['type'], field, keypath, allowed_values)

        if field == 'value':
            if step is not None and index is not None:
                if step not in cfg['pernode_value']:
                    cfg['pernode_value'][step] = {}
                if index not in cfg['pernode_value'][step]:
                    cfg['pernode_value'][step][index] = []
                cfg['pernode_value'][step][index].extend(value)
            elif step is not None:
                if step not in cfg['pernode_value']:
                    cfg['pernode_value'][step] = {}
                if 'default' not in cfg['pernode_value'][step]:
                    cfg['pernode_value'][step]['default'] = []
                cfg['pernode_value'][step]['default'].extend(value)
            else:
                cfg['value'].extend(value)
                cfg['set'] = True
        else:
            cfg[field].extend(value)

        return True

    ###########################################################################
    def clear(self, *keypath):
        '''
        Clears a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.clear` for detailed documentation.
        '''
        cfg = self._search(*keypath)

        if not Schema._is_leaf(cfg):
            raise ValueError(f'Invalid keypath {keypath}: clear() must be called on a complete keypath')

        if cfg['lock']:
            # TODO: log here
            return False

        cfg['value'] = cfg['defvalue']
        cfg['set'] = False

        return True

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
    def record_history(self):
        '''
        Copies all non-empty parameters from current job into the history
        dictionary.
        '''

        # initialize new dict
        jobname = self.get('option','jobname')
        self.cfg['history'][jobname] = {}

        # copy in all empty values of scope job
        allkeys = self.allkeys()
        for key in allkeys:
            # ignore history in case of cumulative history
            if key[0] != 'history':
                scope = self.get(*key, field='scope')
                if not self._keypath_empty(key) and (scope == 'job'):
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

        if field in ('value', 'defvalue'):
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
            return tuple(Schema._normalize_value(v, base_type, error_msg, allowed_values) for v, base_type in zip(value, base_types))

        if sc_type == 'bool':
            if value == 'true': return True
            if value == 'false': return False
            if isinstance(value, bool): return value
            raise TypeError(error_msg)

        try:
            if sc_type == 'int':
                return int(value)

            if sc_type == 'float':
                return float(value)
        except TypeError:
            raise TypeError(error_msg) from None

        if sc_type in ('str', 'file', 'dir'):
            if isinstance(value, str): return value
            else: raise TypeError(error_msg)

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

        if Schema._is_list(field, sc_type):
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
            if not (isinstance(value, str) and value in ('none', 'optional', 'mandatory')):
                raise TypeError(f'Invalid value {value} for field {field}: '
                    'expected one of "none", "optional", or "mandatory"')
            return value

        if field in (
            'type', 'switch', 'shorthelp', 'help', 'unit', 'hashalgo', 'notes',
            'signature'
        ):
            if not isinstance(value, str):
                raise TypeError(error_msg('str'))
            return value

        if field in ('require', 'lock', 'copy', 'set'):
            if value == 'true': return True
            if value == 'false': return False
            if isinstance(value, bool): return value
            else: raise TypeError(error_msg('bool'))

        if field in ('pernode_value',):
            if isinstance(value, dict): return value
            else: raise TypeError(f'Invalid value {value} for field {field}: expected dict')

        raise ValueError(f'Invalid field {field} for keypath {keypath}')

    @staticmethod
    def _is_empty(cfg):
        return not cfg['set']

    @staticmethod
    def _is_leaf(cfg):
        # 'shorthelp' chosen arbitrarily: any mandatory field with a consistent
        # type would work.
        return 'shorthelp' in cfg and isinstance(cfg['shorthelp'], str)

    @staticmethod
    def _is_list(field, type):
        is_list = type.startswith('[')

        if field in ('filehash', 'date', 'author', 'example', 'enum'):
            return True

        if is_list and field in ('signature', 'defvalue', 'value'):
            return True

        return False

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
            if 'defvalue' in cfg[k]:
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
        fout.write(yaml.dump(self.cfg, Dumper=YamlIndentDumper, default_flow_style=False))

    ###########################################################################
    def write_tcl(self, fout, prefix=""):
        '''
        Prints out schema as TCL dictionary
        '''
        manifest_header = os.path.join(utils.PACKAGE_ROOT, 'data', 'sc_manifest_header.tcl')
        with open(manifest_header, 'r') as f:
            fout.write(f.read())
        fout.write('\n')

        allkeys = self.allkeys()

        for key in allkeys:
            typestr = self.get(*key, field='type')
            value = self.get(*key)

            #create a TCL dict
            keystr = ' '.join(key)

            valstr = utils.escape_val_tcl(value, typestr)

            # Turning scalars into lists
            if not (typestr.startswith('[') or typestr.startswith('(')):
                valstr = f'[list {valstr}]'

            # TODO: Temp fix to get rid of empty args
            if valstr=='':
                valstr = f'[list ]'

            outstr = f"{prefix} {keystr} {valstr}\n"

            #print out all non default values
            if 'default' not in key:
                fout.write(outstr)


    ###########################################################################
    def write_csv(self, fout):
        csvwriter = csv.writer(fout)
        csvwriter.writerow(['Keypath', 'Value'])

        allkeys = self.allkeys()
        for key in allkeys:
            keypath = ','.join(key)
            value = self.get(*key)
            if isinstance(value,list):
                for item in value:
                    csvwriter.writerow([keypath, item])
            else:
                csvwriter.writerow([keypath, value])

    ###########################################################################
    def copy(self):
        '''Returns deep copy of Schema object.'''
        return Schema(cfg=self.cfg)

    ###########################################################################
    def prune(self, keeplists=False):
        '''Remove all empty parameters from configuration dictionary.'''
        # When at top of tree loop maxdepth times to make sure all stale
        # branches have been removed, not elegant, but stupid-simple
        # "good enough"

        #10 should be enough for anyone...
        maxdepth = 10

        for _ in range(maxdepth):
            self._prune(self.cfg, keeplists=keeplists)

    ###########################################################################
    def _prune(self, cfg, keeplists=False):
        '''
        Internal recursive function that creates a local copy of the Chip
        schema (cfg) with only essential non-empty parameters retained.

        '''
        # TODO: rename
        localcfg = cfg

        #Prune when the default & value are set to the following
        if keeplists:
            empty = ("null", None)
        else:
            empty = ("null", None, [])

        #Loop through all keys starting at the top
        for k in list(localcfg.keys()):
            #removing all default/template keys
            # reached a default subgraph, delete it
            if k == 'default':
                del localcfg[k]
            # reached leaf-cell
            elif 'help' in localcfg[k].keys():
                del localcfg[k]['help']
            elif 'example' in localcfg[k].keys():
                del localcfg[k]['example']
            elif 'defvalue' in localcfg[k].keys():
                if localcfg[k]['defvalue'] in empty:
                    if 'value' in localcfg[k].keys():
                        if localcfg[k]['value'] in empty:
                            del localcfg[k]
                    else:
                        del localcfg[k]
            #removing stale branches
            elif not localcfg[k]:
                localcfg.pop(k)
            #keep traversing tree
            else:
                self._prune(cfg=localcfg[k], keeplists=keeplists)

    ###########################################################################
    def _keypath_empty(self, key):
        '''
        Utility function to check key for an empty list.
        '''

        emptylist = ("null", None, [])

        value = self.get(*key)
        defvalue = self.get(*key, field='defvalue')
        value_empty = (defvalue in emptylist) and (value in emptylist)

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

class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)
