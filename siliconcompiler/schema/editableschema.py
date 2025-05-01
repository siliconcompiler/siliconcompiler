# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from .parameter import Parameter
from .baseschema import BaseSchema


class EditableSchema:
    '''
    This class provides access to modify the underlying schema.
    This should only be used when creating new schema entries.

    Args:
        schema (:class:`BaseSchema`): schema to modify
    '''

    def __init__(self, schema):
        # Grab manifest from base class
        self.__schema = schema

    def __insert(self, keypath, value, fullkey, clobber):
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
        EditableSchema(new_schema).__insert(keypath, value, fullkey, clobber)

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

    def insert(self, *args, clobber=False):
        '''
        Inserts a :class:`Parameter` or a :class:`BaseSchema` to the schema,
        based on the keypath and value provided in the ``*args``.

        Args:
            args (list): Parameter keypath followed by a item to add.
            clobber (boolean): If true, will overwrite existing value,
                otherwise will raise a KeyError if it is already defined.

        Examples:
            >>> schema.insert('option', 'value', Parameter('str'))
            Adds the keypath [option,value] with a string parameter.
        '''

        value = args[-1]
        keypath = args[0:-1]

        if not keypath:
            raise ValueError("A keypath is required")

        if any([not isinstance(key, str) for key in keypath]):
            raise ValueError("Keypath must only be strings")

        if not isinstance(value, (Parameter, BaseSchema)):
            raise ValueError(f"Value ({type(value)}) must be schema type: Parameter, BaseSchema")

        self.__insert(keypath, value, keypath, clobber=clobber)

    def remove(self, *keypath):
        '''
        Removes a keypath from the schema.

        Args:
            keypath (list): keypath to be removed.

        Examples:
            >>> schema.remove('option', 'value')
            Removes the keypath [option,value] from the schema.
        '''

        if not keypath:
            raise ValueError("A keypath is required")

        if any([not isinstance(key, str) for key in keypath]):
            raise ValueError("Keypath must only be strings")

        self.__remove(keypath, keypath)

    def search(self, *keypath):
        '''
        Finds an item in the schema. This will raise a KeyError if
        the path is not found.

        Args:
            keypath (list): keypath to be found.

        Examples:
            >>> schema.search('option', 'value')
            Returns the parameter stored in at [option,value].
        '''

        if not keypath:
            raise ValueError("A keypath is required")

        if any([not isinstance(key, str) for key in keypath]):
            raise ValueError("Keypath must only be strings")

        return self.__schema._BaseSchema__search(*keypath, require_leaf=False)
