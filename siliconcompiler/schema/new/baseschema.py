# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy
import gzip
import json

import os.path

from .parameter import Parameter


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
                del manifest["default"]
                self.__default._from_dict(data, keypath + ["default"], version=version)
                handled.add("default")

        for key, data in manifest.items():
            obj = self.__manifest.get(key, None)
            if not obj and self.__default:
                obj = self.__default.copy()
                self.__manifest[key] = obj
            if obj:
                obj._from_dict(data, keypath + [key], version=version)
                handled.add(key)
            else:
                missing.add(key)

        return missing, set(self.__manifest.keys()).difference(handled)

    # Manifest methods
    @classmethod
    def from_manifest(cls, filepath=None, cfg=None):
        schema = cls()
        if not filepath and not cfg:
            raise RuntimeError("filepath or dictionary is required")
        if filepath:
            schema.read_manifest(filepath)
        if cfg:
            schema._from_dict(cfg, [])
        return schema

    @staticmethod
    def __open_file(filepath, is_read=True):
        _, ext = os.path.splitext(filepath)
        if ext.lower() == ".gz":
            return gzip.open(filepath, mode="rt" if is_read else "wt", encoding="utf-8")
        return open(filepath, mode="r" if is_read else "w", encoding="utf-8")

    def read_manifest(self, filepath):
        fin = BaseSchema.__open_file(filepath)
        manifest = json.load(fin)
        fin.close()

        self._from_dict(manifest, [])

    def write_manifest(self, filepath):
        fout = BaseSchema.__open_file(filepath, is_read=False)
        json.dump(self.getdict(), fout, indent=2)
        fout.close()

    # Accessor methods
    def __search(self,
                 *keypath,
                 insert_defaults=False,
                 use_default=False,
                 require_leaf=True):
        if len(keypath) == 0:
            if require_leaf:
                raise KeyError
            else:
                return None
        if keypath[0] == "default":
            if use_default:
                key_param = self.__default
            else:
                key_param = None
        else:
            key_param = self.__manifest.get(keypath[0], None)
        if not key_param:
            if insert_defaults and self.__default:
                key_param = self.__default.copy()
                self.__manifest[keypath[0]] = key_param
            elif use_default and self.__default:
                key_param = self.__default
            else:
                raise KeyError
        if isinstance(key_param, BaseSchema):
            if len(keypath) == 1:
                if require_leaf:
                    raise KeyError
                else:
                    return key_param
            return key_param.__search(*keypath[1:],
                                      insert_defaults=insert_defaults,
                                      use_default=use_default,
                                      require_leaf=require_leaf)
        return key_param

    def get(self, *keypath, field='value', step=None, index=None):
        try:
            param = self.__search(*keypath, insert_defaults=False, use_default=True)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")
        if field is None:
            return param
        return param.get(field, step=step, index=index)

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        if len(args) < 2:
            raise KeyError("keypath and value is required")

        *keypath, value = args

        try:
            param = self.__search(*keypath, insert_defaults=True)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")

        return param.set(value, field=field, clobber=clobber, step=step, index=index)

    def add(self, *args, field='value', step=None, index=None):
        if len(args) < 2:
            raise KeyError("keypath and value is required")

        *keypath, value = args

        try:
            param = self.__search(*keypath, insert_defaults=True)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")

        return param.add(value, field=field, step=step, index=index)

    def unset(self, *keypath, step=None, index=None):
        try:
            param = self.__search(*keypath, use_default=True)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")

        param.unset(step=step, index=index)

    def remove(self, *keypath):
        search_path = keypath[0:-1]
        removal_key = keypath[-1]
        if removal_key == "default":
            return

        try:
            key_param = self.__search(*search_path, require_leaf=False)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")

        if not key_param:
            return

        if removal_key not in key_param.__manifest:
            return

        if not key_param.__default:
            return

        if any([key_param.get(*key, field='lock') for key in key_param.allkeys()]):
            return

        del key_param.__manifest[removal_key]

    def valid(self, *keypath, default_valid=False, check_complete=False):
        try:
            param = self.__search(*keypath, use_default=default_valid, require_leaf=False)
        except KeyError:
            return False

        if check_complete:
            return isinstance(param, Parameter)
        return True

    def getkeys(self, *keypath):
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
            if not key_param or isinstance(key_param, Parameter):
                return set()
            return key_param.allkeys(*keypath_prefix[1:], include_default=include_default)

        def add(keys, key, item):
            if isinstance(item, Parameter):
                keys.append((key,))
            else:
                for subkeypath in item.allkeys(include_default=include_default):
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
                return {}
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
