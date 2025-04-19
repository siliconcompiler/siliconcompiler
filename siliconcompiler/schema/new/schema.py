# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from .baseschema import BaseSchema
from .parameter import Parameter

from .schema_cfg import schema_cfg


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
        if current_verison != version:
            self.logger.warning(f"Mismatch in schema versions: {current_verison} != {version}")

        return super()._from_dict(manifest, keypath, version=version)
