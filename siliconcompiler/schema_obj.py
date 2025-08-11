# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import Parameter

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

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return Schema.__name__


##############################################################################
# Main routine
if __name__ == "__main__":
    import json
    print(json.dumps(Schema().getdict(), indent=4, sort_keys=True))
