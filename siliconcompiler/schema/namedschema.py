# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from typing import Dict, Tuple

from .baseschema import BaseSchema


class NamedSchema(BaseSchema):
    '''
    This object provides a named :class:`BaseSchema`.

    Args:
        name (str): name of the schema
    '''

    def __init__(self, name: str = None):
        super().__init__()

        self.set_name(name)

    @property
    def name(self) -> str:
        '''
        Returns the name of the schema
        '''
        try:
            return self.__name
        except AttributeError:
            return None

    def set_name(self, name: str) -> None:
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

    def _getdict_meta(self) -> Dict[str, str]:
        info = super()._getdict_meta()
        info["name"] = self.name
        return info

    @classmethod
    def from_manifest(cls, filepath: str = None, cfg: Dict = None, name: str = None):
        '''
        Create a new schema based on the provided source files.

        The two arguments to this method are mutually exclusive.

        Args:
            filepath (path): Initial manifest.
            cfg (dict): Initial configuration dictionary.
            name (str): name of the schema.
        '''

        if not filepath and cfg is None:
            raise RuntimeError("filepath or dictionary is required")

        schema = cls()
        schema.set_name(name)
        if filepath:
            schema.read_manifest(filepath)
        if cfg:
            schema._from_dict(cfg, [])
        return schema

    def _from_dict(self, manifest: Dict, keypath: Tuple[str], version: str = None):
        if keypath:
            self.__name = keypath[-1]
        elif not self.__name and "__meta__" in manifest and "name" in manifest["__meta__"]:
            self.__name = manifest["__meta__"]["name"]

        return super()._from_dict(manifest, keypath, version=version)

    def copy(self, key: Tuple[str] = None) -> "NamedSchema":
        copy = super().copy(key=key)

        if key and key[-1] != "default":
            copy.__name = key[-1]

        return copy
