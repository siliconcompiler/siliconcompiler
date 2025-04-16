# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy
from enum import Enum
from siliconcompiler.schema.utils import escape_val_tcl


class Scope(Enum):
    GLOBAL = 'global'
    JOB = 'job'
    SCRATCH = 'scratch'


class PerNode(Enum):
    NEVER = 'never'
    OPTIONAL = 'optional'
    REQUIRED = 'required'

    def is_never(self):
        return self == PerNode.NEVER


class Parameter:
    '''
    '''

    GLOBAL_KEY = 'global'
    __PERNODE_FIELDS = ('value', 'filehash', 'date', 'author', 'signature', 'package')

    def __init__(self,
                 type,
                 defvalue=None,
                 scope=Scope.JOB,
                 copy=False,
                 lock=False,
                 hashalgo='sha256',
                 signature=None,
                 unit=None,
                 shorthelp=None,
                 switch=None,
                 example=None,
                 help=None,
                 enum=None,
                 pernode=PerNode.NEVER):
        self.__type = str(type)
        self.__scope = Scope(scope)
        self.__lock = lock

        if switch is None:
            switch = []
        elif isinstance(switch, str):
            switch = [switch]
        self.__switch = switch

        self.__shorthelp = shorthelp

        if example is None:
            example = []
        elif isinstance(example, str):
            example = [example]
        self.__example = example

        self.__help = help

        self.__notes = None

        if self.__type == 'bool':
            if defvalue is None:
                defvalue = False
        if '[' in self.__type:
            if signature is None:
                signature = []
            if defvalue is None:
                defvalue = []

        self.__pernode = PerNode(pernode)
        self.__node = {
            'default': {
                'default': {
                    'value': defvalue,
                    'signature': signature
                }
            }
        }

        self.__enum = None
        if enum is not None:
            self.__enum = [str(e) for e in enum]

        self.__unit = None
        if unit is not None:
            self.__unit = str(unit)

        self.__hashalgo = None
        self.__copy = None
        if 'dir' in self.__type or 'file' in self.__type:
            self.__hashalgo = str(hashalgo)
            self.__copy = bool(copy)
            self.__node['default']['default']['filehash'] = []
            self.__node['default']['default']['package'] = []

        # file only values
        if 'file' in self.__type:
            self.__node['default']['default']['date'] = []
            self.__node['default']['default']['author'] = []

    def __str__(self):
        return str(self.__node)

    def get(self, field='value', step=None, index=None):
        if isinstance(index, int):
            index = str(index)

        if field in Parameter.__PERNODE_FIELDS:
            try:
                return self.__node[step][index][field]
            except KeyError:
                if self.__pernode == PerNode.REQUIRED:
                    return self.__node['default']['default'][field]

            try:
                return self.__node[step][Parameter.GLOBAL_KEY][field]
            except KeyError:
                pass

            try:
                return self.__node[Parameter.GLOBAL_KEY][Parameter.GLOBAL_KEY][field]
            except KeyError:
                return self.__node['default']['default'][field]
        elif field == "type":
            return self.__type
        elif field == "scope":
            return self.__scope
        elif field == "lock":
            return self.__lock
        elif field == "switch":
            return self.__switch
        elif field == "shorthelp":
            return self.__shorthelp
        elif field == "example":
            return self.__example
        elif field == "help":
            return self.__help
        elif field == "notes":
            return self.__notes
        elif field == "pernode":
            return self.__pernode
        elif field == "enum":
            return self.__enum
        elif field == "unit":
            return self.__unit
        elif field == "hashalgo":
            return self.__hashalgo
        elif field == "copy":
            return self.__copy

        raise ValueError(field)

    def set(self, value, field='value', step=None, index=None, clobber=True):
        if field in Parameter.__PERNODE_FIELDS:
            step = step if step is not None else Parameter.GLOBAL_KEY
            index = index if index is not None else Parameter.GLOBAL_KEY

            if step not in self.__node:
                self.__node[step] = {}
            if index not in self.__node[step]:
                self.__node[step][index] = copy.deepcopy(self.__node['default']['default'])
            self.__node[step][index][field] = value
        else:
            # cfg[field] = value
            raise NotImplementedError

    def add(self, value, field='value', step=None, index=None):
        raise NotImplementedError

    def unset(self):
        raise NotImplementedError

    def getdict(self, include_default=True):
        dictvals = {
            "type": self.__type,
            "scope": self.__scope.value,
            "lock": self.__lock,
            "switch": self.__switch.copy(),
            "shorthelp": self.__shorthelp,
            "example": self.__example.copy(),
            "help": self.__help,
            "notes": self.__notes,
            "pernode": self.__pernode.value,
            "node": self.__node.copy()
        }

        if self.__enum:
            dictvals["enum"] = self.__enum.copy()
        if self.__unit:
            dictvals["unit"] = self.__unit
        if self.__hashalgo:
            dictvals["hashalgo"] = self.__hashalgo
        if self.__copy is not None:
            dictvals["copy"] = self.__copy
        return dictvals

    @classmethod
    def from_dict(cls, manifest):
        print("HERE")

    def gettcl(self, step=None, index=None):
        if self.__pernode == PerNode.REQUIRED and (step is None or index is None):
            return None
        if not self.__pernode.is_never():
            value = self.get(step=step, index=index)
        else:
            value = self.get()

        return escape_val_tcl(value, self.__type)
