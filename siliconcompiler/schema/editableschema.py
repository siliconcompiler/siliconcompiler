# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from .parameter import Parameter
from .baseschema import BaseSchema
from .namedschema import NamedSchema

from typing import Union, Tuple


class EditableSchema:
    '''
    This class provides access to modify the underlying schema.
    This should only be used when creating new schema entries.

    Args:
        schema (:class:`BaseSchema`): schema to modify
    '''

    def __init__(self, schema: BaseSchema):
        # Grab manifest from base class
        self.__schema = schema

    def __insert(self,
                 keypath: Tuple[str, ...],
                 value: Union[BaseSchema, Parameter],
                 fullkey: Tuple[str, ...],
                 clobber: bool) -> None:
        key = keypath[0]
        keypath = keypath[1:]

        if len(keypath) == 0:
            if key in self.__schema._BaseSchema__manifest and not clobber:
                raise KeyError(f"[{','.join(fullkey)}] is already defined")

            if isinstance(value, BaseSchema):
                value._BaseSchema__parent = self.__schema
                value._BaseSchema__key = key
                if isinstance(value, NamedSchema):
                    if key == "default":
                        value._NamedSchema__name = None
                    else:
                        value._NamedSchema__name = key

            if key == "default":
                self.__schema._BaseSchema__default = value
            else:
                self.__schema._BaseSchema__manifest[key] = value
            return

        new_schema = BaseSchema()
        new_schema._BaseSchema__parent = self.__schema
        if key == "default":
            if self.__schema._BaseSchema__default:
                new_schema = self.__schema._BaseSchema__default
            else:
                self.__schema._BaseSchema__default = new_schema
        else:
            new_schema = self.__schema._BaseSchema__manifest.setdefault(key, new_schema)
        new_schema._BaseSchema__key = key
        EditableSchema(new_schema).__insert(keypath, value, fullkey, clobber)

    def __remove(self, keypath: Tuple[str, ...], fullkey: Tuple[str, ...]) -> None:
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

    def insert(self, *args: Union[str, BaseSchema, Parameter], clobber: bool = False) -> None:
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
        keypath: Tuple[str, ...] = args[0:-1]

        if not keypath:
            raise ValueError("A keypath is required")

        if any([not isinstance(key, str) for key in keypath]):
            raise ValueError("Keypath must only be strings")

        if not isinstance(value, (Parameter, BaseSchema)):
            raise ValueError(f"Value ({type(value)}) must be schema type: Parameter, BaseSchema")

        self.__insert(keypath, value, keypath, clobber=clobber)

    def remove(self, *keypath: str) -> None:
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

    def search(self, *keypath: str) -> Union[BaseSchema, Parameter]:
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

    def copy(self) -> BaseSchema:
        '''
        Creates a copy of the schema object, disconnected from any parent schema
        '''

        new_schema = self.__schema.copy()
        if new_schema._parent() is not new_schema:
            new_schema._BaseSchema__parent = None
        return new_schema

    def rename(self, name: str):
        '''
        Renames a named schema
        '''

        if not isinstance(self.__schema, NamedSchema):
            raise TypeError("schema must be a named schema")

        if self.__schema._parent() is not self.__schema:
            raise ValueError("object is already in a schema")

        self.__schema._NamedSchema__name = name
