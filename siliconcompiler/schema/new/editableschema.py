# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from .parameter import Parameter
from .baseschema import BaseSchema


class EditableSchema:
    '''
    '''
    def __init__(self, schema):
        # Grab manifest from base class
        self.__schema = schema

    def __add(self, keypath, value, fullkey, clobber):
        key = keypath[0]
        keypath = keypath[1:]

        if len(keypath) == 0:
            if key in self.__schema._BaseSchema__manifest and not clobber:
                raise KeyError(f"[{','.join(fullkey)}] is already defined")

            if key == "default":
                self.__schema._BaseSchema__default = value
            else:
                self.__schema._BaseSchema__manifest[key] = value
            return

        new_schema = BaseSchema()
        if key == "default":
            if self.__schema._BaseSchema__default:
                new_schema = self.__schema._BaseSchema__default
            else:
                self.__schema._BaseSchema__default = new_schema
        else:
            new_schema = self.__schema._BaseSchema__manifest.setdefault(key, new_schema)
        EditableSchema(new_schema).__add(keypath, value, fullkey, clobber)

    def __remove(self, keypath, fullkey):
        key = keypath[0]
        keypath = keypath[1:]

        if key == "default":
            next_param = self.__schema._BaseSchema__default
        else:
            next_param = self.__schema._BaseSchema__manifest.get(key, None)

        if not next_param:
            raise KeyError(f"[{','.join(fullkey)}] cannot be found")

        if len(keypath) == 0:
            if key == "default":
                self.__schema._BaseSchema__default = None
            else:
                del self.__schema._BaseSchema__manifest[key]
        else:
            EditableSchema(next_param).__remove(keypath, fullkey)

    def add(self, *args, clobber=False):
        '''
        '''
        value = args[-1]
        keypath = args[0:-1]

        if not keypath:
            raise ValueError("A keypath is required")

        if any([not isinstance(key, str) for key in keypath]):
            raise ValueError("Keypath must only be strings")

        if not isinstance(value, (Parameter, BaseSchema)):
            raise ValueError(f"Value ({type(value)}) must be schema type: Parameter, BaseSchema")

        self.__add(keypath, value, keypath, clobber=clobber)

    def remove(self, *keypath):
        '''
        '''
        if not keypath:
            raise ValueError("A keypath is required")

        if any([not isinstance(key, str) for key in keypath]):
            raise ValueError("Keypath must only be strings")

        self.__remove(keypath, keypath)

    def search(self, *keypath):
        if not keypath:
            raise ValueError("A keypath is required")

        if any([not isinstance(key, str) for key in keypath]):
            raise ValueError("Keypath must only be strings")

        return self.__schema._BaseSchema__search(*keypath, require_leaf=False)
