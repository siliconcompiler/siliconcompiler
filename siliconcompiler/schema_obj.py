# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy
import os

try:
    import yaml
    _has_yaml = True
except ImportError:
    _has_yaml = False

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import SafeSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import CommandLineSchema
from siliconcompiler.schema import Parameter
from siliconcompiler.schema.parametertype import NodeType
from siliconcompiler.schema.baseschema import json

from siliconcompiler.schema.schema_cfg import schema_cfg


class Schema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_cfg(self)

    @staticmethod
    def _extractversion(manifest):
        schema_version = manifest.get("schemaversion", None)
        if schema_version:
            param = Parameter.from_dict(schema_version, ["schemaversion"], None)
            return param.get()
        return None

    def _from_dict(self, manifest, keypath, version=None):
        # find schema version
        if not version:
            version = Schema._extractversion(manifest)

        current_verison = self.get("schemaversion")
        if version is not None and current_verison != version:
            self.logger.warning(f"Mismatch in schema versions: {current_verison} != {version}")

        return super()._from_dict(manifest, keypath, version=version)


class SchemaTmp(Schema, CommandLineSchema):
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

    # TMP until cleanup
    GLOBAL_KEY = Parameter.GLOBAL_KEY
    _RECORD_ACCESS_IDENTIFIER = "SC_CFG_ACCESS_KEY"

    def __init__(self, cfg=None, manifest=None, logger=None):
        super().__init__()

        self.__logger = logger

        self.__history = {}
        self.__library = {}

        # Use during testing to record calls to Schema.get
        self._init_record_access()
        self._stop_journal()

        if cfg:
            self._from_dict(cfg, [], None)
        if manifest:
            self.read_manifest(manifest)

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        '''
        Sets a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.set` for detailed documentation.
        '''

        if args:
            for section, reference in (("library", self.__library),
                                       ("history", self.__history)):
                if args[0] == section:
                    if len(args) > 1 and args[1] in reference:
                        return reference[args[1]].set(*args[2:],
                                                      field=field,
                                                      clobber=clobber,
                                                      step=step, index=index)
                    return tuple()
        set_ret = super().set(*args, field=field, clobber=clobber, step=step, index=index)
        if set_ret:
            *keypath, value = args
            self.__record_journal("set", keypath, value=value, field=field, step=step, index=index)
        return set_ret

    def add(self, *args, field='value', step=None, index=None):
        '''
        Adds item(s) to a schema parameter list.

        See :meth:`~siliconcompiler.core.Chip.add` for detailed documentation.
        '''
        if args:
            for section, reference in (("library", self.__library),
                                       ("history", self.__history)):
                if args[0] == section:
                    if len(args) > 1 and args[1] in reference:
                        return reference[args[1]].add(*args[2:],
                                                      field=field,
                                                      step=step, index=index)
                    return tuple()
        add_ret = super().add(*args, field=field, step=step, index=index)
        if add_ret:
            *keypath, value = args
            self.__record_journal("add", keypath, value=value, field=field, step=step, index=index)
        return add_ret

    def unset(self, *keypath, step=None, index=None):
        '''
        Unsets a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.unset` for detailed documentation.
        '''
        self.__record_journal("unset", keypath, step=step, index=index)
        super().unset(*keypath, step=step, index=index)

    def remove(self, *keypath):
        '''
        Remove a keypath

        See :meth:`~siliconcompiler.core.Chip.remove` for detailed documentation.
        '''
        self.__record_journal("remove", keypath)
        super().remove(*keypath)

    # TMP needed until clean
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

    # TMP needed until clean
    def _import_group(self, group, name, obj):
        if group == "library":
            self.__library[name] = obj
            return
        if self.valid(group, name):
            self.logger.warning(f'Overwriting existing {group} {name}')
        EditableSchema(self).insert(group, name, obj, clobber=True)

    # TMP needed until clean
    def is_empty(self, *keypath):
        '''
        Utility function to check key for an empty value.
        '''
        return self.get(*keypath, field=None).is_empty()

    # TMP needed until clean
    def has_field(self, *args):
        *keypath, field = args
        return self.get(*keypath, field=field) is not None

    # TMP needed until clean
    def _getvals(self, *keypath, return_defvalue=True):
        """
        Returns all values (global and pernode) associated with a particular parameter.

        Returns a list of tuples of the form (value, step, index). The list is
        in no particular order. For the global value, step and index are None.
        If return_defvalue is True, the default parameter value is added to the
        list in place of a global value if a global value is not set.
        """
        return self.get(*keypath, field=None).getvalues(return_defvalue=return_defvalue)

    # TMP needed until clean
    def _start_journal(self):
        '''
        Start journaling the schema transactions
        '''
        self.__journal = []

    # TMP needed until clean
    def _stop_journal(self):
        '''
        Stop journaling the schema transactions
        '''
        self.__journal = None

    # TMP needed until clean
    def read_journal(self, filename):
        '''
        Reads a manifest and replays the journal
        '''

        with open(filename) as f:
            data = json.loads(f.read())

        self._import_journal(cfg=data)

    # TMP needed until clean
    def _import_journal(self, schema=None, cfg=None):
        '''
        Import the journaled transactions from a different schema
        '''
        journal = []
        if schema:
            if schema.__journal:
                journal = schema.__journal
        if cfg and "__journal__" in cfg:
            journal = cfg["__journal__"]

        for action in journal:
            record_type = action['type']
            keypath = action['key']
            value = action['value']
            field = action['field']
            step = action['step']
            index = action['index']
            try:
                if record_type == 'set':
                    self.set(*keypath, value, field=field, step=step, index=index)
                elif record_type == 'add':
                    self.add(*keypath, value, field=field, step=step, index=index)
                elif record_type == 'unset':
                    self.unset(*keypath, step=step, index=index)
                elif record_type == 'remove':
                    self.remove(*keypath)
                else:
                    raise ValueError(f'Unknown record type {record_type}')
            except Exception as e:
                self.logger.error(f'Exception: {e}')

    def _from_dict(self, manifest, keypath, version=None):
        if "__journal__" in manifest:
            self.__journal = manifest["__journal__"]
            del manifest["__journal__"]

        for section, reference, cls in (("library", self.__library, SafeSchema),
                                        ("history", self.__history, SchemaTmp)):
            if section in manifest:
                for name, sub_manifest in manifest[section].items():
                    reference[name] = cls.from_manifest(cfg=sub_manifest)
                del manifest[section]

        super()._from_dict(manifest, keypath, version=version)

    def getdict(self, *keypath, include_default=True):
        manifest = super().getdict(*keypath, include_default=include_default)

        for section, reference in (("library", self.__library),
                                   ("history", self.__history)):
            if keypath:
                if keypath[0] == section and len(keypath) > 1:
                    return reference[keypath[1]].getdict(*keypath[2:], include_default=True)
                else:
                    continue

            manifest[section] = {}
            for name, obj in reference.items():
                manifest[section][name] = obj.getdict(include_default=include_default)

        if self.__journal:
            manifest["__journal__"] = copy.deepcopy(self.__journal)

        return manifest

    def write_yaml(self, fout):
        if not _has_yaml:
            raise ImportError('yaml package required to write YAML manifest')

        class YamlIndentDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super().increase_indent(flow=flow, indentless=False)

        fout.write(yaml.dump(self.getdict(), Dumper=YamlIndentDumper, default_flow_style=False))

    def write_tcl(self, fout, prefix="", step=None, index=None, template=None):
        tcl_set_cmds = []
        for key in sorted(self.allkeys()):
            # print out all non default values
            if 'default' in key:
                continue

            param = self.get(*key, field=None)

            # create a TCL dict
            keystr = ' '.join([NodeType.to_tcl(keypart, 'str') for keypart in key])

            valstr = param.gettcl(step=step, index=index)
            if valstr is None:
                continue

            # Ensure empty values get something
            if valstr == '':
                valstr = '{}'

            tcl_set_cmds.append(f"{prefix} {keystr} {valstr}")

        if template:
            fout.write(template.render(manifest_dict='\n'.join(tcl_set_cmds),
                                       scroot=os.path.abspath(
                                              os.path.join(os.path.dirname(__file__), '..')),
                                       record_access=self._do_record_access(),
                                       record_access_id=SchemaTmp._RECORD_ACCESS_IDENTIFIER))
        else:
            for cmd in tcl_set_cmds:
                fout.write(cmd + '\n')
            fout.write('\n')

    @property
    def logger(self):
        return self.__logger

    def allkeys(self, *keypath_prefix, include_default=True):
        keys = super().allkeys(*keypath_prefix, include_default=include_default)

        for section, reference in (("library", self.__library),
                                   ("history", self.__history)):
            if keypath_prefix and keypath_prefix[0] != section:
                continue
            for name, obj in reference.items():
                if len(keypath_prefix) > 1 and keypath_prefix[1] != name:
                    continue
                for libkey in obj.allkeys(*keypath_prefix[2:]):
                    keys.add((section, name, *libkey))

        return keys

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
        super().read_manifest(filename)

    def record_history(self):
        '''
        Copies all non-empty parameters from current job into the history
        dictionary.
        '''

        job = self.get("option", "jobname")
        self.__history[job] = self.copy()
        self.__history[job].__history.clear()

    def prune(self):
        raise NotImplementedError

    def change_type(self, *key, type=None):
        raise NotImplementedError

    def get(self, *keypath, field='value', job=None, step=None, index=None):
        """
        Returns a schema parameter field.

        See :meth:`~siliconcompiler.core.Chip.get` for detailed documentation.
        """

        if self.__record_access["recording"]:
            self.__record_access["record"].add(keypath)

        if job is not None:
            return self.history(job).get(*keypath, field=field, step=step, index=index)

        if keypath:
            for section, reference in (("library", self.__library),
                                       ("history", self.__history)):
                if keypath[0] == section:
                    obj = reference.get(keypath[1], None)
                    if not obj:
                        raise KeyError
                    return obj.get(*keypath[2:], field=field, step=step, index=index)

        return super().get(*keypath, field=field, step=step, index=index)

    def history(self, job):
        '''
        Returns a *mutable* reference to ['history', job] as a Schema object.

        If job doesn't currently exist in history, create it with default
        values.

        Args:
            job (str): Name of historical job to return.
        '''
        return self.__history.setdefault(job, SchemaTmp())

    def getkeys(self, *keypath, job=None):
        if job is not None:
            return self.history(job).getkeys(*keypath)
        if keypath:
            for section, reference in (("library", self.__library),
                                       ("history", self.__history)):
                if keypath[0] == section:
                    if len(keypath) == 1:
                        return list(reference.keys())
                    if keypath[1] in reference:
                        return reference[keypath[1]].getkeys(*keypath[2:])
                    return tuple()
        if keypath:
            return super().getkeys(*keypath)
        return tuple([*super().getkeys(), "history", "library"])

    ###########################################################################
    def valid(self, *args, default_valid=False, job=None, check_complete=False):
        if job is not None:
            return self.history(job).valid(*args,
                                           default_valid=default_valid,
                                           check_complete=check_complete)

        if args:
            for section, reference in (("library", self.__library),
                                       ("history", self.__history)):
                if args[0] == section:
                    if len(args) == 1:
                        return True
                    if args[1] in reference:
                        return reference[args[1]].valid(*args[2:],
                                                        default_valid=default_valid,
                                                        check_complete=check_complete)

        return super().valid(*args,
                             default_valid=default_valid,
                             check_complete=check_complete)

    #######################################
    def get_default(self, *keypath):
        '''Returns default value of a parameter.

        Args:
            keypath(list str): Variable length schema key list.
        '''

        param = self.get(*keypath, field=None)
        return param.default

    #######################################
    def _do_record_access(self):
        '''
        Determine if Schema should record calls to .get
        '''
        return False

    #######################################
    def _init_record_access(self):
        '''
        Initialize record access data record
        '''
        self.__record_access = {
            "do": self._do_record_access(),
            "recording": False,
            "record": set()
        }

    #######################################
    def _start_record_access(self):
        '''
        Start recording calls to .get
        '''
        self.__record_access["recording"] = True

    #######################################
    def _stop_record_access(self):
        '''
        Stop recording calls to .get
        '''
        self.__record_access["recording"] = False

    #######################################
    def _get_record_access(self):
        '''
        Return calls to record_access
        '''
        return self.__record_access["record"].copy()


##############################################################################
# Main routine
if __name__ == "__main__":
    import json as main_json
    print(main_json.dumps(SchemaTmp().getdict(), indent=4, sort_keys=True))
