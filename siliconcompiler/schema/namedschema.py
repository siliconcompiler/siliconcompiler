# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from typing import Dict, Tuple, Optional, Set, Union, List

from .baseschema import BaseSchema


class NamedSchema(BaseSchema):
    '''
    This object provides a named :class:`BaseSchema`.

    Args:
        name (str): name of the schema
    '''

    def __init__(self, name: Optional[str] = None):
        super().__init__()

        self.set_name(name)

    @property
    def name(self) -> Optional[str]:
        '''
        Returns the name of the schema
        '''
        try:
            return self.__name
        except AttributeError:
            return None

    def set_name(self, name: Optional[str]) -> None:
        """
        Set the name of this object

        Raises:
            RuntimeError: if called after object name is set.

        Args:
            name (str): name for object
        """

        try:
            if self.__name is not None:
                raise RuntimeError("Cannot call set_name more than once.")
        except AttributeError:
            pass
        if name is not None and "." in name:
            raise ValueError("Named schema object cannot contains: .")
        self.__name = name

    def type(self) -> str:
        """
        Returns the type of this object
        """
        raise NotImplementedError("Must be implemented by the child classes.")

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        raise NotImplementedError("Must be implemented by the child classes.")

    def _getdict_meta(self) -> Dict[str, Optional[Union[str, int, float]]]:
        info = super()._getdict_meta()
        info["name"] = self.name
        return info

    @classmethod
    def from_manifest(cls,
                      filepath: Union[None, str] = None,
                      cfg: Union[None, Dict] = None,
                      name: Optional[str] = None):
        '''
        Create a new schema based on the provided source files.

        The two arguments to this method are mutually exclusive.

        Args:
            filepath (path): Initial manifest.
            cfg (dict): Initial configuration dictionary.
            name (str): name of the schema.
        '''

        schema = super().from_manifest(filepath=filepath, cfg=cfg)
        if name:
            schema.__name = name

        return schema

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        if keypath:
            self.__name = keypath[-1]
        elif not self.__name and "__meta__" in manifest and "name" in manifest["__meta__"]:
            self.__name = manifest["__meta__"]["name"]

        return super()._from_dict(manifest, keypath, version=version)

    def copy(self, key: Optional[Tuple[str, ...]] = None) -> "NamedSchema":
        copy: NamedSchema = super().copy(key=key)

        if key and key[-1] != "default":
            copy.__name = key[-1]

        return copy
