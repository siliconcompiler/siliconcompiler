# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from .parameter import Parameter
from .baseschema import BaseSchema


class SafeSchema(BaseSchema):
    '''
    This object can handle any schema without any class dependencies.
    This is useful when reading in a schema in an external tool.
    '''

    @staticmethod
    def __is_dict_leaf(manifest, keypath, version):
        try:
            return Parameter.from_dict(manifest, keypath, version)
        except:  # noqa E722
            return None

    def _from_dict(self, manifest, keypath, version=None):
        if not isinstance(manifest, dict):
            return

        for key, data in manifest.items():
            obj = SafeSchema.__is_dict_leaf(data, keypath + [key], version)
            if not obj:
                obj = SafeSchema()
                obj._from_dict(data, keypath + [key], version)

            if key == "default":
                self._BaseSchema__default = obj
            else:
                self._BaseSchema__manifest[key] = obj
