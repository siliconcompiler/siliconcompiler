# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy
import logging

from enum import Enum
from pathlib import Path

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
        self.__assert_step_index(field, step, index)

        if field in Parameter.__PERNODE_FIELDS:
            if isinstance(index, int):
                index = str(index)

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

    def __normalize_value(self, value, sctype=None):
        if not sctype:
            sctype = self.__type

        if sctype.startswith('['):
            base_type = sctype[1:-1]

            # Need to try 2 different recursion strategies - if value is a list already, then we can
            # recurse on it directly. However, if that doesn't work, then it might be a
            # list-of-lists/tuples that needs to be wrapped in an outer list, so we try that.
            if isinstance(value, (list, set, tuple)):
                try:
                    return [self.__normalize_value(v, sctype=base_type) for v in value]
                except TypeError:
                    pass

            return [self.__normalize_value(v, sctype=base_type) for v in [value]]

        if sctype.startswith('('):
            base_type = sctype[1:-1]

            # TODO: make parsing more robust to support tuples-of-tuples
            if isinstance(value, str):
                value = value[1:-1].split(',')
            elif not (isinstance(value, tuple) or isinstance(value, list)):
                raise TypeError

            base_types = base_type.split(',')
            if len(value) != len(base_types):
                raise TypeError
            return tuple(self.__normalize_value(v, sctype=base_type) for v, base_type in zip(value, base_types))

        if sctype == 'bool':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                value = value.strip().lower()
                if value == 'true':
                    return True
                if value == 'false':
                    return False
            if isinstance(value, (int, float)):
                return value != 0
            raise TypeError

        if value is None:
            return None

        try:
            if sctype == 'int':
                return int(value)

            if sctype == 'float':
                return float(value)
        except TypeError:
            raise TypeError

        if sctype == 'str':
            if isinstance(value, str):
                return value
            elif isinstance(value, bool):
                return str(value).lower()
            elif isinstance(value, (list, tuple, set)):
                raise TypeError
            else:
                return str(value)

        if sctype in ('file', 'dir'):
            if isinstance(value, (str, Path)):
                return str(value)
            else:
                raise TypeError

        if sctype == 'enum':
            if isinstance(value, str):
                if value in self.__enum:
                    return value
                raise ValueError
            else:
                raise TypeError

        raise ValueError(f'Invalid type specifier: {sctype}')

    def __normalize_field(self, field, value):
        if field in ('author', 'date') and ('file' not in self.__type):
            raise TypeError

        if field in ('copy', 'filehash', 'package', 'hashalgo') and \
           ('file' not in self.__type and 'dir' not in self.__type):
            raise TypeError

        is_list = False
        if field in ('filehash', 'date', 'author', 'example', 'enum', 'switch', 'package'):
            is_list = True
        elif self.is_list and field in ('signature', 'value'):
            is_list = True

        if field == 'package' and is_list:
            if not isinstance(value, list):
                value = [value]
            if not all((v is None or isinstance(v, (str, Path))) for v in value):
                raise TypeError
            return value

        if is_list:
            if not value:
                # Replace none with an empty list
                value = []

            if not isinstance(value, list):
                value = [value]

            if not all(isinstance(v, str) for v in value):
                raise TypeError
            return value

        if field == 'scope':
            # Restricted allowed values
            if isinstance(value, Scope):
                return value
            if not (isinstance(value, str) and value in [val.value for val in Scope]):
                raise TypeError
            return Scope(value)

        if field == 'pernode':
            # Restricted allowed values
            if isinstance(value, PerNode):
                return value.value
            if not (isinstance(value, str) and value in [val.value for val in PerNode]):
                raise TypeError
            return PerNode(value)

        if field in (
            'type', 'switch', 'shorthelp', 'help', 'unit', 'hashalgo', 'notes',
            'signature'
        ):
            return self.__normalize_value(value, sctype='str')

        if field in ('lock', 'copy', 'require'):
            return self.__normalize_value(value, sctype='bool')

        if field in ('node',):
            if isinstance(value, dict):
                return value
            else:
                raise TypeError

        raise ValueError

    def __normalize(self, field, value):
        if field == "value":
            return self.__normalize_value(value)
        else:
            return self.__normalize_field(field, value)

    def __assert_locked(self):
        if self.__lock:
            raise ValueError

    def __assert_step_index(self, field, step, index):
        if field not in Parameter.__PERNODE_FIELDS:
            if step is not None or index is not None:
                raise KeyError
            return

        if self.__pernode == PerNode.NEVER and (step is not None or index is not None):
            raise KeyError

        if self.__pernode == PerNode.REQUIRED and (step is None or index is None):
            raise KeyError

        if step is None and index is not None:
            raise KeyError

        # Step and index for default should be accessed set_/get_default
        if step == 'default':
            raise KeyError

        if index == 'default':
            raise KeyError

    def set(self, value, field='value', step=None, index=None, clobber=True):
        if field != "lock":
            self.__assert_locked()

        self.__assert_step_index(field, step, index)

        if self.is_set(step, index) and not clobber:
            return False

        value = self.__normalize(field, value)

        if field in Parameter.__PERNODE_FIELDS:
            if isinstance(index, int):
                index = str(index)

            step = step if step is not None else Parameter.GLOBAL_KEY
            index = index if index is not None else Parameter.GLOBAL_KEY

            if step not in self.__node:
                self.__node[step] = {}
            if index not in self.__node[step]:
                self.__node[step][index] = copy.deepcopy(self.__node['default']['default'])
            self.__node[step][index][field] = value
        elif field == "type":
            self.__type = value
        elif field == "scope":
            self.__scope = value
        elif field == "lock":
            self.__lock = value
        elif field == "switch":
            self.__switch = value
        elif field == "shorthelp":
            self.__shorthelp = value
        elif field == "example":
            self.__example = value
        elif field == "help":
            self.__help = value
        elif field == "notes":
            self.__notes = value
        elif field == "pernode":
            self.__pernode = value
        elif field == "enum":
            self.__enum = value
        elif field == "unit":
            self.__unit = value
        elif field == "hashalgo":
            self.__hashalgo = value
        elif field == "copy":
            self.__copy = value
        else:
            raise ValueError(field)

        return True

    def add(self, value, field='value', step=None, index=None):
        self.__assert_locked()

        self.__assert_step_index(field, step, index)

        if not self.is_list():
            raise ValueError

        value = self.__normalize(field, value)

        if field in Parameter.__PERNODE_FIELDS:
            if isinstance(index, int):
                index = str(index)

            modified_step = step if step is not None else Parameter.GLOBAL_KEY
            modified_index = index if index is not None else Parameter.GLOBAL_KEY

            if modified_step not in self.__node:
                self.__node[modified_step] = {}
            if modified_index not in self.__node[modified_step]:
                self.__node[modified_step][modified_index] = copy.deepcopy(
                    self.__node['default']['default'])
            self.__node[modified_step][modified_index][field].extend(value)
        elif field == "switch":
            self.__switch.extend(value)
        elif field == "example":
            self.__example.extend(value)
        elif field == "enum":
            self.__enum.extend(value)
        else:
            raise ValueError(field)

        return True

    def unset(self, step=None, index=None):
        if self.__lock:
            # self.logger.debug(f'Failed to set value for {keypath}: parameter is locked')
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

        requires_set = '(' in self.__type

        self.__type = manifest["type"]
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

        if requires_set:
            for step in self.__node:
                for index in self.__node[step]:
                    value = self.__node[step][index]["value"]
                    if value is None:
                        continue
                    self.__node[step][index]["value"] = self.__normalize_value(value)

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
                    vals.append((copy.deepcopy(self.__node[step][index]['value']), step_arg, index_arg))

        if (self.__pernode != PerNode.REQUIRED) and not has_global and return_defvalue:
            vals.append((copy.deepcopy(self.__node['default']['default']['value']), None, None))

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

    def is_set(self, step, index):
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

    @property
    def logger(self):
        return logging.getLogger("siliconcompiler.schema.parameter")
