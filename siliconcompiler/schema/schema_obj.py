# Copyright 2022 Silicon Compiler Authors. All Rights Reserved.

import copy
import csv
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

    Args:
        cfg (dict): Initial configuration dictionary. This may be a subtree of
            the schema. If not provided, the object is initialized to default
            values for all parameters.
    """

    def __init__(self, cfg=None):
        if cfg is None:
            self.cfg = schema_cfg()
        else:
            self.cfg = copy.deepcopy(cfg)

    ###########################################################################
    def get(self, *keypath, field='value', job=None):
        """
        Returns a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.get` for detailed documentation.
        """
        if job is None:
            cfg = self.cfg
        else:
            cfg = self.cfg['history'][job]

        return self._search(cfg, str(keypath), *keypath, field=field, mode='get')

    ###########################################################################
    def set(self, *args, field='value', clobber=True):
        '''
        Sets a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.set` for detailed documentation.
        '''
        keypath = args[:-1]
        value = args[-1]
        return self._search(self.cfg, str(keypath), *keypath, value, field=field, mode='set', clobber=clobber)

    ###########################################################################
    def add(self, *args, field='value'):
        '''
        Adds item(s) to a schema parameter list.

        See :meth:`~siliconcompiler.core.Chip.add` for detailed documentation.
        '''
        keypath = args[:-1]
        value = args[-1]
        return self._search(self.cfg, str(keypath), *keypath, value, field=field, mode='add')

    ###########################################################################
    def getkeys(self, *keypath, job=None):
        """
        Returns a list of schema dictionary keys.

        See :meth:`~siliconcompiler.core.Chip.getkeys` for detailed documentation.
        """
        if job is None:
            cfg = self.cfg
        else:
            cfg = self.cfg['history'][job]

        if len(keypath) > 0:
            keys = list(self._search(cfg, str(keypath), *keypath, mode='getkeys'))
            if 'default' in keys:
                keys.remove('default')
        else:
            keys = list(self._allkeys())

        return keys

    ###########################################################################
    def getdict(self, *keypath):
        """
        Returns a schema dictionary.

        See :meth:`~siliconcompiler.core.Chip.getdict` for detailed
        documentation.
        """
        if len(keypath) > 0:
            localcfg = self._search(self.cfg, str(keypath), *keypath, mode='getcfg')
        # TODO: error condition?

        return copy.deepcopy(localcfg)

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
            valid_keypaths = self.getkeys()

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
        allkeys = self.getkeys()
        for key in allkeys:
            # ignore history in case of cumulative history
            if key[0] != 'history':
                scope = self.get(*key, field='scope')
                if not self._keypath_empty(key) and (scope == 'job'):
                    self._copyparam(self.cfg,
                                    self.cfg['history'][jobname],
                                    key)

    def _search(self, cfg, keypath, *args, field='value', mode='get', clobber=True):
        '''
        Internal recursive function that searches the Chip schema for a
        match to the combination of *args and fields supplied. The function is
        used to set and get data within the dictionary.

        Args:
            cfg(dict): The cfg schema to search
            keypath (str): Concatenated keypath used for error logging.
            args (str): Keypath/value variable list used for access
            field(str): Leaf cell field to access.
            mode(str): Action (set/get/add/getkeys/getkeys)
            clobber(bool): Specifies to clobber (for set action)

        '''

        all_args = list(args)
        param = all_args[0]
        val = all_args[-1]
        empty = [None, 'null', [], 'false']

        # Ensure that all keypath values are strings.
        # Scripts may accidentally pass in [None] if a prior schema entry was unexpectedly empty.
        keys_to_check = args
        if mode in ['set', 'add']:
            # Ignore the value parameter for 'set' and 'add' operations.
            keys_to_check = args[:-1]
        for key in keys_to_check:
            if not isinstance(key, str):
                raise ValueError(f"Key '{key}' in keypath {keypath} is not a string.")

        #set/add leaf cell (all_args=(param,val))
        if (mode in ('set', 'add')) & (len(all_args) == 2):
            # clean error if key not found
            if (not param in cfg) & (not 'default' in cfg):
                raise ValueError(f"Set/Add keypath {keypath} does not exist.")
            else:
                # making an 'instance' of default if not found
                if (not param in cfg) & ('default' in cfg):
                    cfg[param] = copy.deepcopy(cfg['default'])
                list_type =bool(re.match(r'\[', cfg[param]['type']))
                # checking for illegal fields
                if not field in cfg[param] and (field != 'value'):
                    raise ValueError(f"Field '{field}' for keypath {keypath} is not a valid field.")
                # check legality of value
                if field == 'value':
                    (type_ok,type_error) = self._typecheck(cfg[param], param, val)
                    if not type_ok:
                        raise TypeError(type_error)
                # converting python True/False to lower case string
                if (field == 'value') and (cfg[param]['type'] == 'bool'):
                    if val == True:
                        val = "true"
                    elif val == False:
                        val = "false"
                # checking if value has been set
                # TODO: fix clobber!!
                selval = cfg[param]['value']
                # updating values
                if cfg[param]['lock'] == "true":
                    # TODO: add back warning
                    pass
                elif (mode == 'set'):
                    if (field != 'value') or (selval in empty) or clobber:
                        if field in ('copy', 'lock'):
                            # boolean fields
                            if val is True:
                                cfg[param][field] = "true"
                            elif val is False:
                                cfg[param][field] = "false"
                            else:
                                raise TypeError(f'{field} must be set to boolean.')
                        elif field in ('hashalgo', 'scope', 'require', 'type', 'unit',
                                       'shorthelp', 'notes', 'switch', 'help'):
                            # awlays string scalars
                            cfg[param][field] = val
                        elif field in ('example'):
                            # list from default schema (already a list)
                            cfg[param][field] = val
                        elif field in ('signature', 'filehash', 'date', 'author'):
                            # convert to list if appropriate
                            if isinstance(val, list) | (not list_type):
                                cfg[param][field] = val
                            else:
                                cfg[param][field] = [val]
                        elif (not list_type) & (val is None):
                            # special case for None
                            cfg[param][field] = None
                        elif (not list_type) & (not isinstance(val, list)):
                            # convert to string for scalar value
                            cfg[param][field] = str(val)
                        elif list_type & (not isinstance(val, list)):
                            # convert to string for list value
                            cfg[param][field] = [str(val)]
                        elif list_type & isinstance(val, list):
                            # converting tuples to strings
                            if re.search(r'\(', cfg[param]['type']):
                                cfg[param][field] = list(map(str,val))
                            else:
                                cfg[param][field] = val
                        else:
                            raise ValueError(f"Assigning list to scalar for {keypath}")
                    else:
                        # TODO: re-enable
                        #self.logger.debug(f"Ignoring set() to {keypath}, value already set. Use clobber=true to override.")
                        pass
                elif (mode == 'add'):
                    if field in ('filehash', 'date', 'author', 'signature'):
                        cfg[param][field].append(str(val))
                    elif field in ('copy', 'lock'):
                        raise ValueError(f"Illegal use of add() for scalar field {field}.")
                    elif list_type & (not isinstance(val, list)):
                        cfg[param][field].append(str(val))
                    elif list_type & isinstance(val, list):
                        cfg[param][field].extend(val)
                    else:
                        raise ValueError(f"Illegal use of add() for scalar parameter {keypath}.")
                return cfg[param][field]
        #get leaf cell (all_args=param)
        elif len(all_args) == 1:
            if not param in cfg:
                raise ValueError(f"Get keypath {keypath} does not exist.")
            elif mode == 'getcfg':
                return cfg[param]
            elif mode == 'getkeys':
                return cfg[param].keys()
            else:
                if not (field in cfg[param]) and (field!='value'):
                    raise ValueError(f"Field '{field}' not found for keypath {keypath}")
                elif field == 'value':
                    #Select default if no value has been set
                    if field not in cfg[param]:
                        selval = cfg[param]['defvalue']
                    else:
                        selval =  cfg[param]['value']
                    #check for list
                    if bool(re.match(r'\[', cfg[param]['type'])):
                        sctype = re.sub(r'[\[\]]', '', cfg[param]['type'])
                        return_list = []
                        if selval is None:
                            return None
                        for item in selval:
                            if sctype == 'int':
                                return_list.append(int(item))
                            elif sctype == 'float':
                                return_list.append(float(item))
                            elif sctype.startswith('(str,'):
                                if isinstance(item,tuple):
                                    return_list.append(item)
                                else:
                                    tuplestr = re.sub(r'[\(\)\'\s]','',item)
                                    return_list.append(tuple(tuplestr.split(',')))
                            elif sctype.startswith('(float,'):
                                if isinstance(item,tuple):
                                    return_list.append(item)
                                else:
                                    tuplestr = re.sub(r'[\(\)\s]','',item)
                                    return_list.append(tuple(map(float, tuplestr.split(','))))
                            else:
                                return_list.append(item)
                        return return_list
                    else:
                        if selval is None:
                            # Unset scalar of any type
                            scalar = None
                        elif cfg[param]['type'] == "int":
                            #print(selval, type(selval))
                            scalar = int(float(selval))
                        elif cfg[param]['type'] == "float":
                            scalar = float(selval)
                        elif cfg[param]['type'] == "bool":
                            scalar = (selval == 'true')
                        elif re.match(r'\(float', cfg[param]['type']):
                            tuplestr = re.sub(r'[\(\)\s]','',selval)
                            scalar = tuple(map(float, tuplestr.split(',')))
                        elif re.match(r'\(str', cfg[param]['type']):
                            tuplestr = re.sub(r'[\(\)\'\s]','',selval)
                            scalar = tuple(tuplestr.split(','))
                        else:
                            scalar = selval
                        return scalar
                #all non-value fields are strings (or lists of strings)
                else:
                    if cfg[param][field] == 'true':
                        return True
                    elif cfg[param][field] == 'false':
                        return False
                    else:
                        return cfg[param][field]
        #if not leaf cell descend tree
        else:
            ##copying in default tree for dynamic trees
            if not param in cfg and 'default' in cfg:
                cfg[param] = copy.deepcopy(cfg['default'])
            elif not param in cfg:
                raise ValueError(f"Get keypath {keypath} does not exist.")
            all_args.pop(0)
            return self._search(cfg[param], keypath, *all_args, field=field, mode=mode, clobber=clobber)

    ###########################################################################
    def _allkeys(self, cfg=None, keys=None, keylist=None):
        '''
        Returns list of all keypaths in the schema.
        '''
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
    def _typecheck(self, cfg, leafkey, value):
        ''' Schema type checking
        '''
        ok = True
        valuetype = type(value)
        errormsg = ""
        if (not re.match(r'\[',cfg['type'])) & (valuetype==list):
            errormsg = "Value must be scalar."
            ok = False
            # Iterate over list
        else:
            # Create list for iteration
            if valuetype == list:
                valuelist = value
            else:
                valuelist = [value]
                # Make type python compatible
            cfgtype = re.sub(r'[\[\]]', '', cfg['type'])
            for item in valuelist:
                valuetype =  type(item)
                if ((cfgtype != valuetype.__name__) and (item is not None)):
                    tupletype = re.match(r'\([\w\,]+\)',cfgtype)
                    #TODO: check tuples!
                    if tupletype:
                        pass
                    elif cfgtype == 'bool':
                        if not item in ['true', 'false']:
                            errormsg = "Valid boolean values are True/False/'true'/'false'"
                            ok = False
                    elif cfgtype == 'file':
                        pass
                    elif cfgtype == 'dir':
                        pass
                    elif (cfgtype == 'float'):
                        try:
                            float(item)
                        except ValueError:
                            errormsg = "Type mismatch. Cannot cast item to float."
                            ok = False
                    elif (cfgtype == 'int'):
                        try:
                            int(item)
                        except ValueError:
                            errormsg = "Type mismatch. Cannot cast item to int."
                            ok = False
                    elif item is not None:
                        errormsg = "Type mismach."
                        ok = False

        # Logger message
        if type(value) == list:
            printvalue = ','.join(map(str, value))
        else:
            printvalue = str(value)
        errormsg = (errormsg +
                    " Key=" + str(leafkey) +
                    ", Expected Type=" + cfg['type'] +
                    ", Entered Type=" + valuetype.__name__ +
                    ", Value=" + printvalue)


        return (ok, errormsg)

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

        allkeys = self.getkeys()

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

        allkeys = self.getkeys()
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
        return Schema(self.cfg)

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

class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)
