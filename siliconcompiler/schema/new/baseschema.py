# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy
import json
import logging

from siliconcompiler.schema.utils import escape_val_tcl
from siliconcompiler.schema.new.parameter import Parameter


class BaseSchema:
    '''
    '''

    def __init__(self):
        # Data storage for the schema
        self.__manifest = {}
        self.__default = None

    def _from_dict(self, manifest, keypath, version=None):
        handled = set()
        missing = set()

        if self.__default:
            data = manifest.get("default", None)
            if data:
                self.__default._from_dict(data, keypath + ["default"], version=version)
                handled.add("default")

        for key, obj in self.__manifest.items():
            data = manifest.get(key, None)
            if data:
                obj._from_dict(data, keypath + [key], version=version)
                handled.add(key)
            else:
                missing.add(key)

        for key in missing:
            self.logger.warning(f"Failed to match key: [{','.join(keypath + [key])}]")

        if not self.__default:
            for key in set(manifest.keys()).difference(handled):
                self.logger.warning(f"Failed to match key from manifest: [{','.join(keypath + [key])}]")

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

    # Manifest methods
    @classmethod
    def from_manifest(cls, filepath=None, cfg=None):
        schema = cls()
        if not filepath and not cfg:
            raise RuntimeError
        if filepath:
            schema.read_manifest(filepath)
        if cfg:
            schema._from_dict(cfg, [])
        return schema

    def read_manifest(self, filepath):
        with open(filepath) as f:
            manifest = json.load(f)

            self._from_dict(manifest, [])

    def write_manifest(self, filepath):
        if filepath.endswith("json"):
            with open(filepath, 'w') as f:
                json.dump(self.getdict(), f, indent=2)
        if filepath.endswith("tcl"):
            with open(filepath, "w") as f:
                self.__write_manifest_tcl(f, ["dict", "set", "sc_cfg"])

    # Accessor methods
    def __search(self, *keypath, job=None, insert_defaults=False, use_default=False, default_key="default", require_leaf=True):
        if len(keypath) == 0:
            return None
        if keypath[0] == default_key:
            key_param = self.__default
        else:
            key_param = self.__manifest.get(keypath[0], None)
        if not key_param:
            if insert_defaults and self.__default:
                key_param = self.__default.copy()
                self.__manifest[keypath[0]] = key_param
            elif use_default and self.__default:
                key_param = self.__default
            else:
                raise KeyError()
        if isinstance(key_param, BaseSchema):
            if len(keypath) == 1:
                if require_leaf:
                    raise KeyError()
                else:
                    return key_param
            return key_param.__search(*keypath[1:], job=job, insert_defaults=insert_defaults, use_default=use_default, default_key=default_key, require_leaf=require_leaf)
        return key_param

    def get(self, *keypath, field='value', job=None, step=None, index=None):
        param = self.__search(*keypath, job=job, insert_defaults=False, use_default=True)
        if field is None:
            return param
        return param.get(field, step=step, index=index)

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        *keypath, value = args
        param = self.__search(*keypath, insert_defaults=True)
        if field is None:
            return param
        return param.set(value, field=field, clobber=clobber, step=step, index=index)

    def add(self, *args, field='value', step=None, index=None):
        *keypath, value = args
        param = self.__search(*keypath, insert_defaults=True)
        if field is None:
            return param
        return param.add(value, field=field, step=step, index=index)

    def unset(self, *keypath, step=None, index=None):
        param = self.__search(*keypath, use_default=True)
        if isinstance(param, Parameter):
            param.unset(step=step, index=index)
        else:
            raise KeyError

    def remove(self, *keypath):
        search_path = keypath[0:-1]
        removal_key = keypath[-1]
        if removal_key == "default":
            return

        key_param = self.__search(*search_path, require_leaf=False)

        if not key_param:
            return

        if isinstance(key_param, Parameter):
            return

        if removal_key not in key_param.__manifest:
            return

        if not key_param.__default:
            return

        if any([key_param.get(*key, field='lock') for key in key_param.allkeys()]):
            return

        del key_param.__manifest[removal_key]

    def valid(self, *keypath, default_valid=False, job=None, check_complete=False):
        if default_valid:
            default = "default"
        else:
            default = ""

        try:
            param = self.__search(*keypath, default_key=default)
        except KeyError:
            return False

        if not param:
            return False

        if check_complete:
            return isinstance(param, Parameter)
        return True

    def getkeys(self, *keypath, job=None):
        if keypath:
            key, *keypath = keypath
            if key == "default":
                key_param = self.__default
            else:
                key_param = self.__manifest.get(key, None)
            if not key_param:
                return tuple()
            if isinstance(key_param, Parameter):
                return tuple()
            return key_param.getkeys(*keypath)

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

    # Utility functions
    def copy(self):
        return copy.deepcopy(self)

    @property
    def logger(self):
        return logging.getLogger("siliconcompiler.schema")
