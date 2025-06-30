# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from .baseschema import BaseSchema


class NamedSchema(BaseSchema):
    '''
    This object provides a named :class:`BaseSchema`.

    Args:
        name (str): name of the schema
    '''

    def __init__(self, name=None):
        super().__init__()

        self.__name = name

    def name(self):
        '''
        Returns the name of the schema
        '''
        try:
            return self.__name
        except AttributeError:
            return None

    def set_name(self, name):
        """
        Set the name of this object

        Raises:
            RuntimeError: if called after object name is set.

        Args:
            name (str): name for object
        """

        if self.name() is not None:
            raise RuntimeError("Cannot call set_name more than once.")
        self.__name = name

    def _reset(self) -> None:
        """
        Resets the state of the object
        """
        pass

    def type(self) -> str:
        """
        Returns the type of this object
        """
        raise NotImplementedError("Must be implemented by the child classes.")

    @classmethod
    def from_manifest(cls, name, filepath=None, cfg=None):
        '''
        Create a new schema based on the provided source files.

        The two arguments to this method are mutually exclusive.

        Args:
            name (str): name of the schema
            filepath (path): Initial manifest.
            cfg (dict): Initial configuration dictionary.
        '''

        if not filepath and cfg is None:
            raise RuntimeError("filepath or dictionary is required")

        schema = cls(name)
        if filepath:
            schema.read_manifest(filepath)
        if cfg:
            schema._from_dict(cfg, [])
        return schema

    def _from_dict(self, manifest, keypath, version=None):
        if keypath:
            self.__name = keypath[-1]

        return super()._from_dict(manifest, keypath, version=version)

    def copy(self, key=None):
        copy = super().copy(key=key)

        if key and key[-1] != "default":
            copy.__name = key[-1]

        return copy
