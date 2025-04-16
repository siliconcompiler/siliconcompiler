# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy
from siliconcompiler.schema.utils import escape_val_tcl
import json
from siliconcompiler.schema.new.parameter import Parameter


class BaseSchema:
    '''
    '''

    def __init__(self):
        # Data storage for the schema
        self.__manifest = {}
        self.__default = None

    @classmethod
    def _from_dict(cls, manifest):
        pass

    def __write_manifest_tcl(self, fout, key_prefix):
        for key, item in self.__manifest.items():
            next_key = key_prefix + [escape_val_tcl(key, 'str')]
            if isinstance(item, Parameter):
                value = item.gettcl()
                if not value:
                    continue
                fout.write(" ".join(next_key + [value]))
                fout.write("\n")
            else:
                item.__write_manifest_tcl(fout, next_key)

    def write_manifest(self, filepath):
        if filepath.endswith("json"):
            with open(filepath, 'w') as f:
                json.dump(self.getdict(), f, indent=2)
        if filepath.endswith("tcl"):
            with open(filepath, "w") as f:
                self.__write_manifest_tcl(f, ["dict", "set", "sc_cfg"])

    def __search(self, *keypath, job=None, insert_defaults=False):
        if keypath[0] == "default":
            key_param = self.__default
        else:
            key_param = self.__manifest.get(keypath[0], None)
        if not key_param:
            if insert_defaults and self.__default:
                key_param = self.__default.copy()
                self.__manifest[keypath[0]] = key_param
            else:
                raise KeyError()
        if isinstance(key_param, BaseSchema):
            if len(keypath) == 1:
                raise KeyError()
            return key_param.__search(*keypath[1:], job=job, insert_defaults=insert_defaults)
        return key_param

    def get(self, *keypath, field='value', job=None, step=None, index=None):
        param = self.__search(*keypath, job=job, insert_defaults=False)
        if field is None:
            return param
        return param.get(field, step=step, index=index)

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        *keypath, value = args
        param = self.__search(*keypath, insert_defaults=True)
        if field is None:
            return param
        return param.set(value, field=field, step=step, index=index)

    def add(self, *args, field='value', step=None, index=None):
        *keypath, value = args
        param = self.__search(*keypath, insert_defaults=True)
        if field is None:
            return param
        return param.add(value, field=field, step=step, index=index)

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
            if isinstance(key_param, Parameter):
                raise KeyError
            return key_param.getkeys(*keypath[1:])

        return tuple(self.__manifest.keys())

    def allkeys(self, *keypath_prefix, include_default=True):
        if keypath_prefix:
            key_param = self.__manifest.get(keypath_prefix[0], None)
            if not key_param:
                return tuple()
            return key_param.allkeys(*keypath_prefix[1:], include_default=include_default)

        def add(keys, key, item):
            if isinstance(item, Parameter):
                keys.append((key,))
            else:
                for subkeypath in item.allkeys():
                    keys.append((key, *subkeypath))

        keys = []
        if include_default and self.__default:
            add(keys, "default", self.__default)
        for key, item in self.__manifest.items():
            add(keys, key, item)
        return set(keys)

    def getdict(self, *keypath, include_default=True):
        if keypath:
            key_param = self.__manifest.get(keypath[0], None)
            if not key_param:
                return tuple()
            return key_param.getdict(*keypath[1:], include_default=include_default)

        manifest = {}
        if include_default and self.__default:
            manifest["default"] = self.__default.getdict(include_default=include_default)
        for key, item in self.__manifest.items():
            manifest[key] = item.getdict(include_default=include_default)
        return manifest

    def copy(self):
        return copy.deepcopy(self)
