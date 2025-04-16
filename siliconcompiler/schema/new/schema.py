# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from siliconcompiler.schema.new.baseschema import BaseSchema
from siliconcompiler.schema.new.safeschema import SafeSchema
from siliconcompiler.schema.new.parameter import Parameter

from siliconcompiler.schema.new.schema_cfg import schema_cfg


class Schema(BaseSchema):
    def __init__(self):
        super().__init__()

        self.__history = {}
        self.__library = {}

        schema_cfg(self)

    def _from_dict(self, manifest, keypath, version=None):
        # find schema version
        schema_version = manifest.get("schemaversion", None)
        if not version and schema_version:
            param = Parameter.from_dict(schema_version, ["schemaversion"], None)
            version = param.get()

        current_verison = self.get("schemaversion")
        if current_verison != version:
            self.logger.warning(f"Mismatch in schema versions: {current_verison} != {version}")

        # Handle history and library special
        del manifest["library"]
        del manifest["history"]

        super()._from_dict(manifest, keypath, version=version)

    def getdict(self, *keypath, include_default=True):
        if keypath:
            if keypath[0] == "history":
                return []
            if keypath[0] == "library":
                return []
            return super().getdict(*keypath, include_default=include_default)

        manifest = super().getdict(include_default=include_default)

        # Handle history and library special
        manifest["history"] = {}
        for name, obj in self.__history.items():
            manifest["history"][name] = obj.getdict(include_default=include_default)
        manifest["library"] = {}
        for name, obj in self.__library.items():
            manifest["library"][name] = obj.getdict(include_default=include_default)

        return manifest


if __name__ == "__main__":
    schema = Schema()
    schema.set("pdk", "sky", "node", "5")
    schema.write_manifest("test.json")

    # safe = SafeSchema.from_manifest(filepath="test.json")
    safe = SafeSchema.from_manifest(cfg=schema.getdict())
    # safe.unlock()
    # safe.set('option', 'var', 'blah', 'blah')
    # safe.lock()
    # safe.set('option', 'var', 'blah', 'blah')
    safe.write_manifest("test2.json")
