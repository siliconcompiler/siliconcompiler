# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from siliconcompiler.schema.new.parameter import Parameter
from siliconcompiler.schema.new.baseschema import BaseSchema


class EditableSchema:
    '''
    '''
    def __init__(self, schema):
        # Grab manifest from base class
        self.__schema = schema

    def __add(self, keypath, value, fullkey):
        key = keypath[0]
        keypath = keypath[1:]

        if len(keypath) == 0:
            if key in self.__schema._BaseSchema__manifest:
                raise KeyError(f"{fullkey} is already defined")

            if key == "default":
                self.__schema._BaseSchema__default = value
            else:
                self.__schema._BaseSchema__manifest[key] = value
            return

        new_schema = BaseSchema()
        if key == "default":
            self.__schema._BaseSchema__default = new_schema
        else:
            new_schema = self.__schema._BaseSchema__manifest.setdefault(key, new_schema)
        EditableSchema(new_schema).__add(keypath, value, fullkey)

    def add(self, *args):
        '''
        '''
        value = args[-1]
        keypath = args[0:-1]

        if not isinstance(value, (Parameter, BaseSchema)):
            raise ValueError("value must be schema type: Parameter, BaseSchema")

        self.__add(keypath, value, keypath)
