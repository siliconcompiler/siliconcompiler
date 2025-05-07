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

    @property
    def name(self):
        '''
        Returns the name of the schema
        '''
        return self.__name

    def set_name(self, name):
        '''
        Sets the name of the schema

        Args:
            name (str): new name for the schema
        '''
        self.__name = name

    def _from_dict(self, manifest, keypath, version=None):
        if keypath:
            self.__name = keypath[-1]

        return super()._from_dict(manifest, keypath, version=version)
