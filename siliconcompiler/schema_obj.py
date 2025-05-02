# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

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

        schema = EditableSchema(self)
        schema.insert("history", BaseSchema())
        schema.insert("library", BaseSchema())

        self.__logger = logger

        if cfg:
            self._from_dict(cfg, [], None)
        if manifest:
            self.read_manifest(manifest)

    def _from_dict(self, manifest, keypath, version=None):
        for section, cls in (("library", SafeSchema),
                             ("history", SchemaTmp)):
            if section in manifest:
                for name, sub_manifest in manifest[section].items():
                    EditableSchema(self).insert(section, name, cls.from_manifest(cfg=sub_manifest))
                del manifest[section]

        super()._from_dict(manifest, keypath, version=version)

    def write_yaml(self, fout):
        if not _has_yaml:
            raise ImportError('yaml package required to write YAML manifest')

        class YamlIndentDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super().increase_indent(flow=flow, indentless=False)

        fout.write(yaml.dump(self.getdict(), Dumper=YamlIndentDumper, default_flow_style=False))

    def write_tcl(self, fout, prefix="", step=None, index=None, template=None, record=False):
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
                                       record_access=record,
                                       record_access_id=SchemaTmp._RECORD_ACCESS_IDENTIFIER))
        else:
            for cmd in tcl_set_cmds:
                fout.write(cmd + '\n')
            fout.write('\n')

    @property
    def logger(self):
        return self.__logger

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
        EditableSchema(self).insert("history", job, self.copy(), clobber=True)

    def prune(self):
        raise NotImplementedError

    def change_type(self, *key, type=None):
        raise NotImplementedError

    def history(self, job):
        '''
        Returns a *mutable* reference to ['history', job] as a Schema object.

        If job doesn't currently exist in history, create it with default
        values.

        Args:
            job (str): Name of historical job to return.
        '''
        try:
            return EditableSchema(self).search("history", job)
        except KeyError:
            blank = SchemaTmp()
            EditableSchema(self).insert("history", job, blank)
            return blank

    #######################################
    def get_default(self, *keypath):
        '''Returns default value of a parameter.

        Args:
            keypath(list str): Variable length schema key list.
        '''

        param = self.get(*keypath, field=None)
        return param.default


##############################################################################
# Main routine
if __name__ == "__main__":
    import json as main_json
    print(main_json.dumps(SchemaTmp().getdict(), indent=4, sort_keys=True))
