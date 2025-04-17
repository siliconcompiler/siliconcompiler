# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from siliconcompiler.schema.new.baseschema import BaseSchema
from siliconcompiler.schema.new.editableschema import EditableSchema
from siliconcompiler.schema.new.parameter import Parameter

from siliconcompiler.schema.new.schema_cfg import schema_cfg


class Schema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_cfg(self)

        schema = EditableSchema(self)
        schema.add("library", BaseSchema())
        schema.add("history", BaseSchema())

    def _from_dict(self, manifest, keypath, version=None):
        # find schema version
        schema_version = manifest.get("schemaversion", None)
        if not version and schema_version:
            param = Parameter.from_dict(schema_version, ["schemaversion"], None)
            version = param.get()

        current_verison = self.get("schemaversion")
        if current_verison != version:
            self.logger.warning(f"Mismatch in schema versions: {current_verison} != {version}")

        super()._from_dict(manifest, keypath, version=version)

    def get(self, *keypath, field='value', job=None, step=None, index=None):
        if job is not None:
            job_data = EditableSchema(self).search("history", job)
            return job_data.get(*keypath, field=field, step=step, index=index)
        return super().get(*keypath, field=field, step=step, index=index)
