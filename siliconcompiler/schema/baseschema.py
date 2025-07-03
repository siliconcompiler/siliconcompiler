# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy

try:
    import gzip
    _has_gzip = True
except ModuleNotFoundError:
    _has_gzip = False

try:
    import orjson as json
    _has_orjson = True
except ModuleNotFoundError:
    import json
    _has_orjson = False

import os.path

from .parameter import Parameter
from .journal import Journal


class BaseSchema:
    '''
    This class maintains the access and file IO operations for the schema.
    It can be modified using :class:`EditableSchema`.
    '''

    def __init__(self):
        self.__manifest = {}
        self.__default = None
        self.__journal = Journal()
        self.__parent = self

    def _from_dict(self, manifest, keypath, version=None):
        '''
        Decodes a dictionary into a schema object

        Args:
            manifest (dict): Manifest to decide.
            keypath (list of str): Path to the current keypath.
            version (packaging.Version): Version of the dictionary schema
        '''

        handled = set()
        missing = set()

        if "__journal__" in manifest:
            self.__journal.from_dict(manifest["__journal__"])

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
        '''
        Create a new schema based on the provided source files.

        The two arguments to this method are mutually exclusive.

        Args:
            filepath (path): Initial manifest.
            cfg (dict): Initial configuration dictionary.
        '''

        if not filepath and cfg is None:
            raise RuntimeError("filepath or dictionary is required")

        schema = cls()
        if filepath:
            schema.read_manifest(filepath)
        if cfg:
            schema._from_dict(cfg, [])
        return schema

    @staticmethod
    def __open_file(filepath, is_read=True):
        _, ext = os.path.splitext(filepath)
        if ext.lower() == ".gz":
            if not _has_gzip:
                raise RuntimeError("gzip is not available")
            return gzip.open(filepath, mode="rt" if is_read else "wt", encoding="utf-8")
        return open(filepath, mode="r" if is_read else "w", encoding="utf-8")

    def read_manifest(self, filepath):
        """
        Reads a manifest from disk and replaces the current data with the data in the file.

        Args:
            filename (path): Path to a manifest file to be loaded.

        Examples:
            >>> schema.read_manifest('mychip.json')
            Loads the file mychip.json into the current Schema object.
        """

        fin = BaseSchema.__open_file(filepath)
        manifest = json.loads(fin.read())
        fin.close()

        self._from_dict(manifest, [])

    def write_manifest(self, filepath):
        '''
        Writes the manifest to a file.

        Args:
            filename (filepath): Output filepath.

        Examples:
            >>> schema.write_manifest('mydump.json')
            Dumps the current manifest into mydump.json
        '''

        fout = BaseSchema.__open_file(filepath, is_read=False)

        if _has_orjson:
            manifest_str = json.dumps(self.getdict(), option=json.OPT_INDENT_2).decode()
        else:
            manifest_str = json.dumps(self.getdict(), indent=2)
        fout.write(manifest_str)

        fout.close()

    # Accessor methods
    def __search(self,
                 *keypath,
                 insert_defaults=False,
                 use_default=False,
                 require_leaf=True,
                 complete_path=None):
        if len(keypath) == 0:
            if require_leaf:
                raise KeyError
            else:
                return self

        if complete_path is None:
            complete_path = []
        complete_path.append(keypath[0])

        if keypath[0] == "default":
            key_param = self.__default
        else:
            key_param = self.__manifest.get(keypath[0], None)
        if not key_param:
            if insert_defaults and self.__default:
                if isinstance(self.__default, Parameter) and self.__default.get(field='lock'):
                    raise KeyError
                key_param = self.__default.copy(key=complete_path)
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
                                      require_leaf=require_leaf,
                                      complete_path=complete_path)
        return key_param

    def get(self, *keypath, field='value', step=None, index=None):
        """
        Returns a parameter field from the schema.

        Returns a schema parameter field based on the keypath provided in the
        ``*keypath``. The returned type is consistent with the type field of the parameter.
        Accessing a non-existent keypath raises a KeyError.

        Args:
            keypath (list of str): Keypath to access.
            field (str): Parameter field to fetch, if None will return the :class:`Parameter`
                object stored, if field is 'schema' the schema at this keypath will be returned.
            step (str): Step name to access for parameters that may be specified
                on a per-node basis.
            index (str): Index name to access for parameters that may be specified
                on a per-node basis.

        Returns:
            Value found for the keypath and field provided.

        Examples:
            >>> foundry = schema.get('pdk', 'virtual', 'foundry')
            Returns the value of [pdk,virtual,foundry].
        """

        try:
            require_leaf = True
            if field == 'schema':
                require_leaf = False
            param = self.__search(
                *keypath,
                insert_defaults=False,
                use_default=True,
                require_leaf=require_leaf)
            if field == 'schema':
                if isinstance(param, Parameter):
                    raise ValueError(f"[{','.join(keypath)}] is a complete keypath")
                self.__journal.record("get", keypath, field=field, step=step, index=index)
                param.__journal = self.__journal.get_child(*keypath)
                return param
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")
        if field is None:
            return param

        try:
            get_ret = param.get(field, step=step, index=index)
            self.__journal.record("get", keypath, field=field, step=step, index=index)
            return get_ret
        except Exception as e:
            new_msg = f"error while accessing [{','.join(keypath)}]: {e.args[0]}"
            e.args = (new_msg, *e.args[1:])
            raise e

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        '''
        Sets a schema parameter field.

        Sets a schema parameter field based on the keypath and value provided in
        the ``*args``. New schema entries are automatically created for keypaths
        that overlap with 'default' entries.

        Args:
            args (list): Parameter keypath followed by a value to set.
            field (str): Parameter field to set.
            clobber (bool): Existing value is overwritten if True.
            step (str): Step name to set for parameters that may be specified
                on a per-node basis.
            index (str): Index name to set for parameters that may be specified
                on a per-node basis.

        Examples:
            >>> schema.set('design', 'top')
            Sets the [design] value to 'top'
        '''

        if len(args) < 2:
            raise KeyError("keypath and value is required")

        *keypath, value = args

        try:
            param = self.__search(*keypath, insert_defaults=True)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")

        try:
            set_ret = param.set(value, field=field, clobber=clobber,
                                step=step, index=index)
            if set_ret:
                self.__journal.record("set", keypath, value=value, field=field,
                                      step=step, index=index)
            return set_ret
        except Exception as e:
            new_msg = f"error while setting [{','.join(keypath)}]: {e.args[0]}"
            e.args = (new_msg, *e.args[1:])
            raise e

    def add(self, *args, field='value', step=None, index=None):
        '''
        Adds item(s) to a schema parameter list.

        Adds item(s) to schema parameter list based on the keypath and value
        provided in the ``*args``.  New schema entries are automatically created
        for keypaths that overlap with 'default' entries.

        Args:
            args (list): Parameter keypath followed by a value to add.
            field (str): Parameter field to modify.
            step (str): Step name to modify for parameters that may be specified
                on a per-node basis.
            index (str): Index name to modify for parameters that may be specified
                on a per-node basis.

        Examples:
            >>> schema.add('input', 'rtl', 'verilog', 'hello.v')
            Adds the file 'hello.v' to the [input,rtl,verilog] key.
        '''

        if len(args) < 2:
            raise KeyError("keypath and value is required")

        *keypath, value = args

        try:
            param = self.__search(*keypath, insert_defaults=True)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")

        try:
            add_ret = param.add(value, field=field, step=step, index=index)
            if add_ret:
                self.__journal.record("add", keypath, value=value, field=field,
                                      step=step, index=index)
            return add_ret
        except Exception as e:
            new_msg = f"error while adding to [{','.join(keypath)}]: {e.args[0]}"
            e.args = (new_msg, *e.args[1:])
            raise e

    def unset(self, *keypath, step=None, index=None):
        '''
        Unsets a schema parameter.

        This method effectively undoes any previous calls to :meth:`set()` made to
        the given keypath and step/index. For parameters with required or no
        per-node values, unsetting a parameter always causes it to revert to its
        default value, and future calls to :meth:`set()` with ``clobber=False`` will
        once again be able to modify the value.

        If you unset a particular step/index for a parameter with optional
        per-node values, note that the newly returned value will be the global
        value if it has been set. To completely return the parameter to its
        default state, the global value has to be unset as well.

        ``unset()`` has no effect if called on a parameter that has not been
        previously set.

        Args:
            keypath (list): Parameter keypath to clear.
            step (str): Step name to unset for parameters that may be specified
                on a per-node basis.
            index (str): Index name to unset for parameters that may be specified
                on a per-node basis.
        '''

        try:
            param = self.__search(*keypath, use_default=True)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")

        try:
            param.unset(step=step, index=index)
            self.__journal.record("unset", keypath, step=step, index=index)
        except Exception as e:
            new_msg = f"error while unsetting [{','.join(keypath)}]: {e.args[0]}"
            e.args = (new_msg, *e.args[1:])
            raise e

    def remove(self, *keypath):
        '''
        Remove a schema parameter and its subparameters.

        Args:
            keypath (list): Parameter keypath to clear.
        '''

        search_path = keypath[0:-1]
        removal_key = keypath[-1]
        if removal_key == "default":
            return

        try:
            key_param = self.__search(*search_path, require_leaf=False)
        except KeyError:
            raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")

        if removal_key not in key_param.__manifest:
            return

        if not key_param.__default:
            return

        if any([key_param.get(*key, field='lock') for key in key_param.allkeys()]):
            return

        del key_param.__manifest[removal_key]
        self.__journal.record("remove", keypath)

    def valid(self, *keypath, default_valid=False, check_complete=False):
        """
        Checks validity of a keypath.

        Checks the validity of a parameter keypath and returns True if the
        keypath is valid and False if invalid.

        Args:
            keypath (list of str): keypath to check if valid.
            default_valid (bool): Whether to consider "default" in valid
            keypaths as a wildcard.
            check_complete (bool): Require the keypath be a complete path.

        Returns:
            Boolean indicating validity of keypath.

        Examples:
            >>> check = schema.valid('design')
            Returns True
            >>> check = schema.valid('blah')
            Returns False.
            >>> check = schema.valid('metric', 'foo', '0', 'tasktime', default_valid=True)
            Returns True, even if "foo" and "0" aren't in current configuration.
        """

        try:
            param = self.__search(*keypath, use_default=default_valid, require_leaf=False)
        except KeyError:
            return False

        if check_complete:
            return isinstance(param, Parameter)
        return True

    def getkeys(self, *keypath):
        """
        Returns a tuple of schema dictionary keys.

        Searches the schema for the keypath provided and returns a list of
        keys found, excluding the generic 'default' key.

        Args:
            keypath (list of str): Keypath to get keys for.

        Returns:
            tuple of keys found for the keypath provided.

        Examples:
            >>> keylist = chip.getkeys('pdk')
            Returns all keys for the [pdk] keypath.
        """

        if keypath:
            try:
                key_param = self.__search(*keypath, require_leaf=False)
            except KeyError:
                raise KeyError(f"[{','.join(keypath)}] is not a valid keypath")
            if isinstance(key_param, Parameter):
                return tuple()
        else:
            key_param = self

        return tuple(key_param.__manifest.keys())

    def allkeys(self, *keypath, include_default=True):
        '''
        Returns all keypaths in the schema as a set of tuples.

        Arg:
            keypath (list of str): Keypath prefix to search under. The
                returned keypaths do not include the prefix.
        '''

        if keypath:
            key_param = self.__manifest.get(keypath[0], None)
            if not key_param or isinstance(key_param, Parameter):
                return set()
            return key_param.allkeys(*keypath[1:], include_default=include_default)

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

    def getdict(self, *keypath, include_default=True, values_only=False):
        """
        Returns a schema dictionary.

        Searches the schema for the keypath provided and returns a complete
        dictionary.

        Args:
            keypath (list of str): Variable length ordered schema key list
            include_default (boolean): If true will include default key paths
            values_only (boolean): If true will only return values

        Returns:
            A schema dictionary

        Examples:
            >>> pdk = schema.getdict('pdk')
            Returns the complete dictionary found for the keypath [pdk]
        """

        if keypath:
            key_param = self.__manifest.get(keypath[0], None)
            if not key_param:
                return {}
            return key_param.getdict(*keypath[1:],
                                     include_default=include_default,
                                     values_only=values_only)

        manifest = {}
        if include_default and self.__default:
            manifest_dict = self.__default.getdict(include_default=include_default,
                                                   values_only=values_only)
            if manifest_dict or not values_only:
                manifest["default"] = manifest_dict
        for key, item in self.__manifest.items():
            manifest_dict = item.getdict(include_default=include_default,
                                         values_only=values_only)
            if manifest_dict or not values_only:
                manifest[key] = manifest_dict

        if not values_only and self.__journal.has_journaling():
            manifest["__journal__"] = self.__journal.get()

        return manifest

    # Utility functions
    def copy(self, key=None):
        """
        Returns a copy of this schema.

        Args:
            key (list of str): keypath to this schema
        """

        parent = self.__parent
        self.__parent = None
        schema_copy = copy.deepcopy(self)
        self.__parent = parent

        if self is not self.__parent:
            schema_copy.__parent = self.__parent
        else:
            schema_copy.__parent = schema_copy

        return schema_copy

    def find_files(self, *keypath, missing_ok=False, step=None, index=None,
                   packages=None, collection_dir=None, cwd=None):
        """
        Returns absolute paths to files or directories based on the keypath
        provided.

        The keypath provided must point to a schema parameter of type file, dir,
        or lists of either. Otherwise, it will trigger an error.

        Args:
            keypath (list of str): Variable length schema key list.
            missing_ok (bool): If True, silently return None when files aren't
                found. If False, print an error and set the error flag.
            step (str): Step name to access for parameters that may be specified
                on a per-node basis.
            index (str): Index name to access for parameters that may be specified
                on a per-node basis.
            packages (dict of resolvers): dirctionary of path resolvers for package
                paths, these can either be a path or a callable function
            collection_dir (path): optional path to a collections directory
            cwd (path): optional path to current working directory, this will default
                to os.getcwd() if not provided.

        Returns:
            If keys points to a scalar entry, returns an absolute path to that
            file/directory, or None if not found. It keys points to a list
            entry, returns a list of either the absolute paths or None for each
            entry, depending on whether it is found.

        Examples:
            >>> chip.find_files('input', 'verilog')
            Returns a list of absolute paths to source files, as specified in
            the schema.
        """

        param = self.get(*keypath, field=None)
        paramtype = param.get(field='type')
        if 'file' not in paramtype and 'dir' not in paramtype:
            raise TypeError(f'Cannot find files on [{",".join(keypath)}], must be a path type')

        paths = param.get(field=None, step=step, index=index)

        is_list = True
        if not isinstance(paths, list):
            is_list = False
            if paths.get():
                paths = [paths]
            else:
                paths = []

        # Ignore collection directory if it does not exist
        if collection_dir and not os.path.exists(collection_dir):
            collection_dir = None

        if cwd is None:
            cwd = os.getcwd()

        if packages is None:
            packages = {}

        resolved_paths = []
        for path in paths:
            search_paths = []

            package = path.get(field="package")
            if package:
                if package not in packages:
                    raise ValueError(f"Resolver for {package} not provided")
                package_path = packages[package]
                if isinstance(package_path, str):
                    search_paths.append(os.path.abspath(package_path))
                elif callable(package_path):
                    search_paths.append(package_path())
                else:
                    raise TypeError(f"Resolver for {package} is not a recognized type")
            else:
                if cwd:
                    search_paths.append(os.path.abspath(cwd))

            try:
                resolved_path = path.resolve_path(search=search_paths,
                                                  collection_dir=collection_dir)
            except FileNotFoundError:
                resolved_path = None
                if not missing_ok:
                    if package:
                        raise FileNotFoundError(
                            f'Could not find "{path.get()}" in {package} [{",".join(keypath)}]')
                    else:
                        raise FileNotFoundError(
                            f'Could not find "{path.get()}" [{",".join(keypath)}]')
            resolved_paths.append(resolved_path)

        if not is_list:
            if not resolved_paths:
                return None
            return resolved_paths[0]
        return resolved_paths

    def check_filepaths(self, ignore_keys=None, logger=None,
                        packages=None, collection_dir=None, cwd=None):
        '''
        Verifies that paths to all files in manifest are valid.

        Args:
            ignore_keys (list of keypaths): list of keypaths to ignore while checking
            logger (:class:`logging.Logger`): optional logger to use to report errors
            packages (dict of resolvers): dirctionary of path resolvers for package
                paths, these can either be a path or a callable function
            collection_dir (path): optional path to a collections directory
            cwd (path): optional path to current working directory, this will default
                to os.getcwd() if not provided.

        Returns:
            True if all file paths are valid, otherwise False.
        '''

        if ignore_keys is None:
            ignore_keys = set()
        else:
            ignore_keys = set([
                tuple(keypath) for keypath in ignore_keys
            ])

        error = False

        for keypath in self.allkeys():
            if keypath in ignore_keys:
                continue

            param = self.get(*keypath, field=None)
            paramtype = param.get(field='type')

            if 'file' not in paramtype and 'dir' not in paramtype:
                continue

            for check_files, step, index in param.getvalues():
                if not check_files:
                    # nothing set so continue
                    continue

                found_files = BaseSchema.find_files(
                    self, *keypath, missing_ok=True, step=step, index=index,
                    packages=packages, collection_dir=collection_dir, cwd=cwd)

                if not param.is_list():
                    check_files = [check_files]
                    found_files = [found_files]

                for check_file, found_file in zip(check_files, found_files):
                    if not found_file:
                        error = True
                        if logger:
                            node_indicator = ""
                            if step is not None:
                                if index is None:
                                    node_indicator = f" ({step})"
                                else:
                                    node_indicator = f" ({step}/{index})"

                            logger.error(f"Parameter [{','.join(keypath)}]{node_indicator} path "
                                         f"{check_file} is invalid")

        return not error

    def _parent(self, root=False):
        '''
        Returns the parent of this schema section, if root is true the root parent
        will be returned.

        Args:
            root (bool): if true, returns the root of the schemas.
        '''
        if not root:
            return self.__parent
        if self.__parent is self:
            return self
        return self.__parent._parent(root=root)
