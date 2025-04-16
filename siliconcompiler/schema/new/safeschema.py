# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from .parameter import Parameter
from .baseschema import BaseSchema


class SafeSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        self.lock()

    def unlock(self):
        self.__locked = False

    def lock(self):
        self.__locked = True

    @staticmethod
    def __is_dict_leaf(manifest, keypath, version):
        try:
            return Parameter.from_dict(manifest, keypath, version)
        except:  # noqa E722
            return None

    def _from_dict(self, manifest, keypath, version=None):
        for key, data in manifest.items():
            obj = SafeSchema.__is_dict_leaf(data, keypath + [key], version)
            if not obj:
                obj = SafeSchema()
                obj._from_dict(data, keypath + [key], version)

            if key == "default":
                self._BaseSchema__default = obj
            else:
                self._BaseSchema__manifest[key] = obj

    def set(self, *args, **kwargs):
        if self.__locked:
            raise RuntimeError
        return super().set(*args, **kwargs)

    def add(self, *args, **kwargs):
        if self.__locked:
            raise RuntimeError
        return super().add(*args, **kwargs)
