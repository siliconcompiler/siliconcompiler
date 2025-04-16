# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from siliconcompiler.schema.utils import escape_val_tcl
from enum import Enum


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


class SchemaParameter:
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

        if field in SchemaParameter.__PERNODE_FIELDS:
            try:
                return self.__node[step][index][field]
            except KeyError:
                if self.__pernode == PerNode.REQUIRED:
                    return self.__node['default']['default'][field]

            try:
                return self.__node[step][SchemaParameter.GLOBAL_KEY][field]
            except KeyError:
                pass

            try:
                return self.__node[SchemaParameter.GLOBAL_KEY][SchemaParameter.GLOBAL_KEY][field]
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
        pass

    def add(self, value, field='value', step=None, index=None):
        pass

    def unset(self):
        pass

    def getdict(self):
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

    def gettcl(self, step=None, index=None):
        if self.__pernode == PerNode.REQUIRED and (step is None or index is None):
            return None
        if not self.__pernode.is_never():
            value = self.get(step=step, index=index)
        else:
            value = self.get()

        return escape_val_tcl(value, self.__type)


class EditableSchema:
    '''
    '''
    def __init__(self, schema):
        # Grab manifest from base class
        self.__manifest = schema._BaseSchema__manifest

    def __add(self, keypath, value, fullkey):
        if len(keypath) == 1:
            key = keypath[0]
            if key in self.__manifest:
                raise KeyError(f"{fullkey} is already defined")
            self.__manifest[key] = value
            return

        new_schema = self.__manifest.setdefault(keypath[0], BaseSchema())
        EditableSchema(new_schema).__add(keypath[1:], value, fullkey)

    def add(self, *keypath):
        '''
        '''
        value = keypath[-1]
        keypath = keypath[0:-1]

        if not isinstance(value, (SchemaParameter, BaseSchema)):
            raise ValueError("value must be schema type: SchemaParameter, BaseSchema")

        self.__add(keypath, value, keypath)


class BaseSchema:
    '''
    '''

    def __init__(self):
        # Data storage for the schema
        self.__manifest = {}

    def __write_manifest_tcl(self, fout, key_prefix):
        for key, item in self.__manifest.items():
            next_key = key_prefix + [escape_val_tcl(key, 'str')]
            if isinstance(item, SchemaParameter):
                value = item.gettcl()
                if not value:
                    continue
                fout.write(" ".join(next_key + [value]))
                fout.write("\n")
            else:
                item.__write_manifest_tcl(fout, next_key)

    def write_manifest(self, filepath):
        if filepath.endswith("json"):
            import json
            with open(filepath, 'w') as f:
                json.dump(self.getdict(), f, indent=2)
        if filepath.endswith("tcl"):
            with open(filepath, "w") as f:
                self.__write_manifest_tcl(f, ["dict", "set", "sc_cfg"])

    def __get(self, *keypath, job=None):
        key_param = self.__manifest.get(keypath[0], None)
        if not key_param:
            raise KeyError()
        if isinstance(key_param, BaseSchema):
            if len(keypath) == 1:
                raise KeyError()
            return key_param.__get(*keypath[1:], job=job)
        return key_param

    def get(self, *keypath, field='value', job=None, step=None, index=None):
        return self.__get(*keypath, job=job).get(field, step=step, index=index)

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        key_param = self.__manifest.get(args[0], None)
        if not key_param:
            raise KeyError()
        if isinstance(key_param, BaseSchema):
            if len(args) == 2:
                raise KeyError()
            return key_param.set(*args[1:], field=field, clobber=clobber, step=step, index=index)
        return key_param.set(args[0], step=step, index=index)

    def add(self, *args, field='value', step=None, index=None):
        key_param = self.__manifest.get(args[0], None)
        if not key_param:
            raise KeyError()
        if isinstance(key_param, BaseSchema):
            if len(args) == 2:
                raise KeyError()
            return key_param.add(*args[1:], field=field, step=step, index=index)
        return key_param.add(args[0], step=step, index=index)

    def unset(self, *keypath, step=None, index=None):
        pass

    def remove(self, *keypath):
        pass

    def valid(self, *args, default_valid=False, job=None, check_complete=False):
        pass

    def getkeys(self, *keypath, job=None):
        if keypath:
            key_param = self.__manifest.get(keypath[0], None)
            if not key_param:
                return tuple()
            if isinstance(key_param, SchemaParameter):
                raise KeyError
            return key_param.getkeys(*keypath[1:])
        return tuple(self.__manifest.keys())

    def allkeys(self, *keypath_prefix):
        if keypath_prefix:
            key_param = self.__manifest.get(keypath_prefix[0], None)
            if not key_param:
                return tuple()
            return key_param.allkeys(*keypath_prefix[1:])

        keys = []
        for key, item in self.__manifest.items():
            if isinstance(item, SchemaParameter):
                keys.append((key,))
            else:
                for subkeypath in item.allkeys():
                    keys.append((key, *subkeypath))
        return set(keys)

    def getdict(self, *keypath):
        if keypath:
            key_param = self.__manifest.get(keypath[0], None)
            if not key_param:
                return tuple()
            return key_param.getdict(*keypath[1:])

        manifest = {}
        for key, item in self.__manifest.items():
            manifest[key] = item.getdict()
        return manifest


class Schema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.add("schemaversion", SchemaParameter(
            'str',
            scope=Scope.GLOBAL,
            defvalue='9.9.9',
            shorthelp="Schema version number",
            lock=True,
            switch="-schemaversion <str>",
            example=["api: chip.get('schemaversion')"],
            help="""SiliconCompiler schema version number."""))


class PDK(BaseSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.add("foundry", SchemaParameter(
            "str",
            scope=Scope.GLOBAL,
            shorthelp="PDK: foundry name",
            switch="-pdk_foundry 'pdkname <str>'",
            example=["cli: -pdk_foundry 'asap7 virtual'",
                     "api: chip.set('pdk', 'asap7', 'foundry', 'virtual')"],
            help="""
            Name of foundry corporation. Examples include intel, gf, tsmc,
            samsung, skywater, virtual. The \'virtual\' keyword is reserved for
            simulated non-manufacturable processes."""))
        schema.add("node", SchemaParameter(
            "float",
            scope=Scope.GLOBAL,
            unit='nm',
            shorthelp="PDK: process node",
            switch="-pdk_node 'pdkname <float>'",
            example=["cli: -pdk_node 'asap7 130'",
                     "api: chip.set('pdk', 'asap7', 'node', 130)"],
            help="""
            Approximate relative minimum dimension of the process target specified
            in nanometers. The parameter is required for flows and tools that
            leverage the value to drive technology dependent synthesis and APR
            optimization. Node examples include 180, 130, 90, 65, 45, 32, 22 14,
            10, 7, 5, 3."""))


class Design(BaseSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.add("name", SchemaParameter(
            "str"))
        schema.add("input", "default", "default", SchemaParameter(
            "file"))


if __name__ == "__main__":
    schema = Schema()

    print(schema.getdict())
    edit_schema = EditableSchema(schema)
    edit_schema.add("pdk", "default", PDK())
    edit_schema.add("design", Design())
    # print(schema.getdict())

    # print(schema.get("pdk", "default", "foundry"))
    print(schema.allkeys())
    schema.write_manifest("test.tcl")
