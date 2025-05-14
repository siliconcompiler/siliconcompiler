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
        return self.__name

    def _from_dict(self, manifest, keypath, version=None):
        if keypath:
            self.__name = keypath[-1]

        return super()._from_dict(manifest, keypath, version=version)

    def copy(self, key=None):
        copy = super().copy(key=key)

        if not self.__name and key and key[-1] != "default":
            copy.__name = key[-1]

        return copy
