# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from typing import Dict, Tuple

from .parameter import Parameter
from .baseschema import BaseSchema


class SafeSchema(BaseSchema):
    '''
    This object can handle any schema without any class dependencies.
    This is useful when reading in a schema in an external tool.
    '''

    @staticmethod
    def __is_dict_leaf(manifest: Dict, keypath: Tuple[str], version: str) -> Parameter:
        try:
            return Parameter.from_dict(manifest, keypath, version)
        except:  # noqa E722
            return None

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return "SafeSchema"

    def _from_dict(self, manifest: Dict, keypath: Tuple[str], version: str = None) -> None:
        if not isinstance(manifest, dict):
            return

        if "__meta__" in manifest:
            del manifest["__meta__"]

        for key, data in manifest.items():
            obj = SafeSchema.__is_dict_leaf(data, keypath + [key], version)
            if not obj:
                obj = SafeSchema()
                obj._from_dict(data, keypath + [key], version)

            if key == "default":
                self._BaseSchema__default = obj
            else:
                self._BaseSchema__manifest[key] = obj

    @classmethod
    def from_manifest(cls, filepath: str = None, cfg: Dict = None) -> "SafeSchema":
        if filepath:
            cfg = BaseSchema._read_manifest(filepath)

        if cfg and "__meta__" in cfg:
            del cfg["__meta__"]

        return super().from_manifest(filepath=None, cfg=cfg)
