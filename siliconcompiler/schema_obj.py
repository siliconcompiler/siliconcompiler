# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import SafeSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import CommandLineSchema
from siliconcompiler.schema import Parameter
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
            return tuple([int(v) for v in param.get().split('.')])
        return None

    def _from_dict(self, manifest, keypath, version=None):
        # find schema version
        if not version:
            version = Schema._extractversion(manifest)

        current_verison = tuple([int(v) for v in self.get("schemaversion").split('.')])
        if version is None:
            version = current_verison

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

    def record_history(self):
        '''
        Copies all non-empty parameters from current job into the history
        dictionary.
        '''

        job = self.get("option", "jobname")
        EditableSchema(self).insert("history", job, self.copy(), clobber=True)

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


##############################################################################
# Main routine
if __name__ == "__main__":
    import json as main_json
    print(main_json.dumps(SchemaTmp().getdict(), indent=4, sort_keys=True))
