# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy

from enum import Enum
from pathlib import Path

from siliconcompiler.schema.utils import escape_val_tcl
from .parametervalue import NodeValue


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
                 require=False,
                 defvalue=None,
                 scope=Scope.JOB,
                 copy=False,
                 lock=False,
                 hashalgo='sha256',
                 signature=None,
                 notes=None,
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
        self.__require = require

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

        self.__notes = notes

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
        if enum is not None and 'enum' in self.__type:
            self.__enum = [str(e) for e in enum]

        self.__unit = None
        if unit is not None and ('int' in self.__type or 'float' in self.__type):
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
        self.__assert_step_index(field, step, index)

        if field in Parameter.__PERNODE_FIELDS:
            if isinstance(index, int):
                index = str(index)

            try:
                return copy.deepcopy(self.__node[step][index][field])
            except KeyError:
                if self.__pernode == PerNode.REQUIRED:
                    return copy.deepcopy(self.__node['default']['default'][field])

            try:
                return copy.deepcopy(self.__node[step][Parameter.GLOBAL_KEY][field])
            except KeyError:
                pass

            try:
                return copy.deepcopy(self.__node[Parameter.GLOBAL_KEY][Parameter.GLOBAL_KEY][field])
            except KeyError:
                return copy.deepcopy(self.__node['default']['default'][field])
        elif field == "type":
            return self.__type
        elif field == "scope":
            return self.__scope
        elif field == "lock":
            return self.__lock
        elif field == "switch":
            return copy.deepcopy(self.__switch)
        elif field == "shorthelp":
            return self.__shorthelp
        elif field == "example":
            return copy.deepcopy(self.__example)
        elif field == "help":
            return self.__help
        elif field == "notes":
            return self.__notes
        elif field == "pernode":
            return self.__pernode
        elif field == "enum":
            return copy.deepcopy(self.__enum)
        elif field == "unit":
            return self.__unit
        elif field == "hashalgo":
            return self.__hashalgo
        elif field == "copy":
            return self.__copy
        elif field == "require":
            return self.__require

        raise ValueError(f'"{field}" is not a valid field')

    def __assert_locked(self):
        if self.__lock:
            raise ValueError("parameter is locked")

    def __assert_step_index(self, field, step, index):
        if field not in Parameter.__PERNODE_FIELDS:
            if step is not None or index is not None:
                raise KeyError('step and index are only valid for'
                               f': {", ".join(Parameter.__PERNODE_FIELDS)}')
            return

        if self.__pernode == PerNode.NEVER and (step is not None or index is not None):
            raise KeyError('use of step and index are not valid')

        if self.__pernode == PerNode.REQUIRED and (step is None or index is None):
            raise KeyError('step and index are required')

        if step is None and index is not None:
            raise KeyError('step is required if index is provided')

        # Step and index for default should be accessed set_/get_default
        if step == 'default':
            raise KeyError('illegal step name: default is reserved')

        if index == 'default':
            raise KeyError('illegal index name: default is reserved')

    def set(self, value, field='value', step=None, index=None, clobber=True):
        if field != "lock":
            self.__assert_locked()

        self.__assert_step_index(field, step, index)

        if self.is_set(step, index) and not clobber:
            return False

        if field in Parameter.__PERNODE_FIELDS:
            if isinstance(index, int):
                index = str(index)

            step = step if step is not None else Parameter.GLOBAL_KEY
            index = index if index is not None else Parameter.GLOBAL_KEY

            is_dir = 'dir' in self.__type
            is_file = 'file' in self.__type

            if field == "value":
                field_type = self.__type
                field_enum = self.__enum
            elif field == "signature":
                field_type = "[str]" if self.is_list() else "str"
                field_enum = None
            elif field == "filehash" and (is_dir or is_file):
                field_type = "[str]" if self.is_list() else "str"
                field_enum = None
            elif field == "package" and (is_dir or is_file):
                field_type = "[str]" if self.is_list() else "str"
                field_enum = None
            elif field == "date" and is_file:
                field_type = "[str]" if self.is_list() else "str"
                field_enum = None
            elif field == "author" and is_file:
                field_type = "[str]"
                field_enum = None
            else:
                raise ValueError(f'"{field}" is not a valid field')

            if step not in self.__node:
                self.__node[step] = {}
            if index not in self.__node[step]:
                self.__node[step][index] = copy.deepcopy(self.__node['default']['default'])
            self.__node[step][index][field] = NodeValue.normalize(value,
                                                                  field_type,
                                                                  enum=field_enum)
        elif field == "type":
            self.__type = NodeValue.normalize(value, "str")
        elif field == "scope":
            if isinstance(value, Scope):
                self.__scope = value
            else:
                self.__scope = Scope(NodeValue.normalize(value,
                                                         "str",
                                                         enum=[v.value for v in Scope]))
        elif field == "lock":
            self.__lock = NodeValue.normalize(value, "bool")
        elif field == "switch":
            self.__switch = NodeValue.normalize(value, "[str]")
        elif field == "shorthelp":
            self.__shorthelp = NodeValue.normalize(value, "str")
        elif field == "example":
            self.__example = NodeValue.normalize(value, "[str]")
        elif field == "help":
            self.__help = NodeValue.normalize(value, "str")
        elif field == "notes":
            self.__notes = NodeValue.normalize(value, "str")
        elif field == "pernode":
            if isinstance(value, PerNode):
                self.__pernode = value
            else:
                self.__pernode = PerNode(NodeValue.normalize(value,
                                                             "str",
                                                             enum=[v.value for v in PerNode]))
        elif field == "enum":
            self.__enum = NodeValue.normalize(value, "[str]")
        elif field == "unit":
            self.__unit = NodeValue.normalize(value, "str")
        elif field == "hashalgo":
            self.__hashalgo = NodeValue.normalize(value, "str")
        elif field == "copy":
            self.__copy = NodeValue.normalize(value, "bool")
        elif field == "require":
            self.__require = NodeValue.normalize(value, "bool")
        else:
            raise ValueError(f'"{field}" is not a valid field')

        return True

    def add(self, value, field='value', step=None, index=None):
        self.__assert_locked()

        self.__assert_step_index(field, step, index)

        if not self.is_list():
            raise ValueError("add can only be used on lists")

        if field in Parameter.__PERNODE_FIELDS:
            if isinstance(index, int):
                index = str(index)

            modified_step = step if step is not None else Parameter.GLOBAL_KEY
            modified_index = index if index is not None else Parameter.GLOBAL_KEY

            is_dir = 'dir' in self.__type
            is_file = 'file' in self.__type

            if field == "value":
                field_type = self.__type
                field_enum = self.__enum
            elif field == "signature":
                field_type = "[str]"
                field_enum = None
            elif field == "filehash" and (is_dir or is_file):
                field_type = "[str]"
                field_enum = None
            elif field == "package" and (is_dir or is_file):
                field_type = "[str]"
                field_enum = None
            elif field == "date" and is_file:
                field_type = "[str]"
                field_enum = None
            elif field == "author" and is_file:
                field_type = "[str]"
                field_enum = None
            else:
                raise ValueError(f'"{field}" is not a valid field')

            if modified_step not in self.__node:
                self.__node[modified_step] = {}
            if modified_index not in self.__node[modified_step]:
                self.__node[modified_step][modified_index] = copy.deepcopy(
                    self.__node['default']['default'])
            self.__node[modified_step][modified_index][field].extend(
                NodeValue.normalize(value, field_type, enum=field_enum))
        elif field == "switch":
            self.__switch.extend(NodeValue.normalize(value, "[str]"))
        elif field == "example":
            self.__example.extend(NodeValue.normalize(value, "[str]"))
        elif field == "enum":
            self.__enum.extend(NodeValue.normalize(value, "[str]"))
        else:
            raise ValueError(f'"{field}" is not a valid field')

        return True

    def unset(self, step=None, index=None):
        if self.__lock:
            return False

        if isinstance(index, int):
            index = str(index)

        if step is None:
            step = Parameter.GLOBAL_KEY
        if index is None:
            index = Parameter.GLOBAL_KEY

        try:
            del self.__node[step][index]
        except KeyError:
            # If this key doesn't exist, silently continue - it was never set
            pass

        return True

    def getdict(self, include_default=True):
        dictvals = {
            "type": self.__type,
            "require": self.__require,
            "scope": self.__scope.value,
            "lock": self.__lock,
            "switch": self.__switch.copy(),
            "shorthelp": self.__shorthelp,
            "example": self.__example.copy(),
            "help": self.__help,
            "notes": self.__notes,
            "pernode": self.__pernode.value,
            "node": copy.deepcopy(self.__node)
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
    def from_dict(cls, manifest, keypath, version):
        # create a dummy param
        param = cls("str")
        param._from_dict(manifest, keypath, version)
        return param

    def _from_dict(self, manifest, keypath, version):
        if self.__lock:
            return

        self.__type = manifest["type"]
        self.__require = manifest["require"]
        self.__scope = Scope(manifest["scope"])
        self.__lock = manifest["lock"]
        self.__switch = manifest["switch"]
        self.__shorthelp = manifest["shorthelp"]
        self.__example = manifest["example"]
        self.__help = manifest["help"]
        self.__notes = manifest["notes"]
        self.__pernode = PerNode(manifest["pernode"])
        self.__node = manifest["node"]

        self.__enum = manifest.get("enum", self.__enum)
        self.__unit = manifest.get("unit", self.__unit)
        self.__hashalgo = manifest.get("hashalgo", self.__hashalgo)
        self.__copy = manifest.get("copy", self.__copy)

        requires_set = '(' in self.__type

        if requires_set:
            for step in self.__node:
                for index in self.__node[step]:
                    value = self.__node[step][index]["value"]
                    if value is None:
                        continue
                    self.__node[step][index]["value"] = NodeValue.normalize(value,
                                                                            self.__type,
                                                                            enum=self.__enum)

    def gettcl(self, step=None, index=None):
        if self.__pernode == PerNode.REQUIRED and (step is None or index is None):
            return None
        if not self.__pernode.is_never():
            value = self.get(step=step, index=index)
        else:
            value = self.get()

        return escape_val_tcl(value, self.__type)

    def getvalues(self, return_defvalue=True):
        vals = []
        has_global = False
        for step in self.__node:
            if step == 'default':
                continue

            for index in self.__node[step]:
                step_arg = None if step == Parameter.GLOBAL_KEY else step
                index_arg = None if index == Parameter.GLOBAL_KEY else index
                if 'value' in self.__node[step][index]:
                    if step_arg is None and index_arg is None:
                        has_global = True
                    vals.append(
                        (copy.deepcopy(self.__node[step][index]['value']), step_arg, index_arg))

        if (self.__pernode != PerNode.REQUIRED) and not has_global and return_defvalue:
            vals.append(
                (copy.deepcopy(self.__node['default']['default']['value']), None, None))

        return vals

    def copy(self):
        return copy.deepcopy(self)

    # Utility functions
    def is_list(self):
        return self.__type.startswith('[')

    def is_empty(self):
        '''
        Utility function to check key for an empty value.
        '''
        empty = (None, [])

        values = self.getvalues()
        return all([value in empty for value, _, _ in values])

    def is_set(self, step=None, index=None):
        '''
        Returns whether a user has set a value for this parameter.

        A value counts as set if a user has set a global value OR a value for
        the provided step/index.
        '''
        if Parameter.GLOBAL_KEY in self.__node and \
                Parameter.GLOBAL_KEY in self.__node[Parameter.GLOBAL_KEY] and \
                'value' in self.__node[Parameter.GLOBAL_KEY][Parameter.GLOBAL_KEY]:
            # global value is set
            return True

        if step is None:
            return False
        if index is None:
            index = Parameter.GLOBAL_KEY

        return step in self.__node and \
            index in self.__node[step] and \
            'value' in self.__node[step][index]
