# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from typing import Dict, Tuple, Optional, Union, List, Set

from .parameter import Parameter
from .baseschema import BaseSchema, LazyLoad


class SafeSchema(BaseSchema):
    '''
    This object can handle any schema without any class dependencies.
    This is useful when reading in a schema in an external tool.
    '''

    @staticmethod
    def __is_dict_leaf(manifest: Dict,
                       keypath: List[str],
                       version: Optional[Tuple[int, ...]]) -> Optional[Parameter]:
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

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.OFF) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        if not isinstance(manifest, dict):
            return set(), set()

        if "__meta__" in manifest:
            del manifest["__meta__"]

        lazyload = LazyLoad.OFF

        for key, data in manifest.items():
            obj = SafeSchema.__is_dict_leaf(data, list(keypath) + [key], version)
            if not obj:
                obj = SafeSchema()
                obj._from_dict(data, list(keypath) + [key], version=version, lazyload=lazyload)

            if key == "default":
                self._BaseSchema__default = obj
            else:
                self._BaseSchema__manifest[key] = obj

        return set(), set()

    @classmethod
    def from_manifest(cls,
                      filepath: Union[None, str] = None,
                      cfg: Union[None, Dict] = None,
                      lazyload: bool = False) -> "SafeSchema":
        if filepath:
            cfg = BaseSchema._read_manifest(filepath)

        def rm_meta(manifest):
            if not isinstance(manifest, dict):
                return
            if manifest and "__meta__" in manifest:
                del manifest["__meta__"]
            for section in manifest.values():
                rm_meta(section)

        rm_meta(cfg)

        return super().from_manifest(filepath=None, cfg=cfg, lazyload=False)
