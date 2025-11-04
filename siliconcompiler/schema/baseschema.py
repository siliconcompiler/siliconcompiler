# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import contextlib
import copy
import importlib
import logging

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

from enum import Enum, auto
from functools import cache
from typing import Dict, Type, Tuple, Union, Set, Callable, List, Optional, TextIO, Iterable, Any

from .parameter import Parameter, NodeValue
from .journal import Journal
from ._metadata import version


class LazyLoad(Enum):
    """
    Controls manifest loading
    """
    OFF = auto()  # load entire schema immediately
    ON = auto()  # store schema but do not load it
    FORWARD = auto()  # load the current section but do not load children

    @property
    def next(self) -> "LazyLoad":
        """
        Returns the next state for lazy loading
        """
        if self == LazyLoad.ON:
            return LazyLoad.ON
        if self == LazyLoad.FORWARD:
            return LazyLoad.ON
        return LazyLoad.OFF

    @property
    def is_enforced(self) -> bool:
        """
        Returns true when the current section should not be loaded.
        """
        return self == LazyLoad.ON


class BaseSchema:
    '''
    This class maintains the access and file IO operations for the schema.
    It can be modified using :class:`EditableSchema`.
    '''

    _version_key = "schemaversion"
    __version = tuple([int(v) for v in version.split('.')])

    def __init__(self):
        self.__manifest: Dict[str, Union["BaseSchema", Parameter]] = {}
        self.__default: Optional[Union["BaseSchema", Parameter]] = None
        self.__journal: Journal = Journal()
        self.__parent: Optional["BaseSchema"] = None
        self.__active: Optional[Dict] = None
        self.__key: Optional[str] = None
        self.__lazy: Optional[Tuple[Optional[Tuple[int, ...]], Dict]] = None

    @property
    def __is_root(self) -> bool:
        '''
        Returns true if the object is the root of the schema
        '''
        try:
            return self.__parent is None
        except AttributeError:
            return True

    @property
    def _keypath(self) -> Tuple[str, ...]:
        '''
        Returns the key to the current section of the schema
        '''
        if self.__is_root:
            return tuple()
        try:
            parentpath = self.__parent._keypath
            key = self.__key
        except AttributeError:
            # Guard against partially setup parents during serialization
            return tuple()
        return tuple([*parentpath, key])

    @staticmethod
    @cache
    def __get_child_classes() -> Dict[str, Type["BaseSchema"]]:
        """
        Returns all known subclasses of BaseSchema
        """
        def recurse(cls):
            subclss = set()
            subclss.add(cls)
            for subcls in cls.__subclasses__():
                subclss.update(recurse(subcls))
            return subclss

        # Resolve true base
        cls_mapping = {}
        for cls in recurse(BaseSchema):
            try:
                cls_mapping.setdefault(cls._getdict_type(), set()).add(cls)
            except NotImplementedError:
                pass

        # Build lookup table
        cls_map = {}
        for cls_type, clss in cls_mapping.items():
            for cls in clss:
                cls_map[f"{cls.__module__}/{cls.__name__}"] = cls

            if len(clss) > 1:
                found = False
                for cls in clss:
                    if cls.__name__ == cls_type:
                        cls_map[cls_type] = cls
                        found = True
                        break
                if not found:
                    candidates = sorted(f"{c.__module__}/{c.__name__}" for c in clss)
                    raise RuntimeError(
                        f"Ambiguous schema type '{cls_type}'. Candidates: {', '.join(candidates)}"
                    )
            else:
                cls_map[cls_type] = list(clss)[0]
        return cls_map

    @staticmethod
    @cache
    def __load_schema_class(cls_name: str) -> Optional[Type["BaseSchema"]]:
        """
        Load a schema class from a string
        """
        try:
            module_name, cls_name = cls_name.split("/")
        except (ValueError, AttributeError):
            return None

        try:
            module = importlib.import_module(module_name)
        except (ImportError, ModuleNotFoundError, SyntaxError):
            return None

        cls = getattr(module, cls_name, None)
        if not cls:
            return None
        if not issubclass(cls, BaseSchema):
            raise TypeError(f"{cls_name} must be a BaseSchema type")
        return cls

    @staticmethod
    def __process_meta_section(meta: Dict[str, str]) -> Optional[Type["BaseSchema"]]:
        """
        Handle __meta__ section of the schema by loading the appropriate class
        """
        cls_map = BaseSchema.__get_child_classes()

        # Lookup object, use class first, then type
        cls_name = meta.get("class", None)
        cls = None
        if cls_name:
            cls = cls_map.get(cls_name, None)
            if not cls:
                cls = BaseSchema.__load_schema_class(cls_name)
        if not cls:
            cls = cls_map.get(meta.get("sctype", None), None)
        return cls

    @staticmethod
    def __extractversion(manifest: Dict) -> Optional[Tuple[int, ...]]:
        schema_version = manifest.get(BaseSchema._version_key, None)
        if schema_version:
            param = Parameter.from_dict(schema_version,
                                        tuple([BaseSchema._version_key]),
                                        None)
            return tuple([int(v) for v in param.get().split('.')])
        return None

    def __ensure_lazy_elab(self):
        if not self.__lazy:
            return

        version, manifest = self.__lazy
        self.__lazy = None

        self._from_dict(manifest, self._keypath, version=version, lazyload=LazyLoad.FORWARD)

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        '''
        Decodes a dictionary into a schema object

        Args:
            manifest (dict): Manifest to decide.
            keypath (list of str): Path to the current keypath.
            version ((int, int, int)): Version of the dictionary schema
        '''
        # find schema version
        if not version:
            version = BaseSchema.__extractversion(manifest)

            if version is None:
                version = BaseSchema.__version

        handled = set()
        missing = set()

        if "__journal__" in manifest:
            self.__journal.from_dict(manifest["__journal__"])
            if lazyload != LazyLoad.ON:
                del manifest["__journal__"]

        if lazyload == LazyLoad.ON:
            self.__lazy = (version, manifest)
            return set(), set()

        if "__meta__" in manifest:
            del manifest["__meta__"]

        if self.__default:
            data = manifest.pop("default", None)
            if data:
                if isinstance(self.__default, BaseSchema):
                    self.__default._from_dict(data, tuple([*keypath, "default"]), version=version,
                                              lazyload=lazyload.next)
                else:
                    self.__default._from_dict(data, tuple([*keypath, "default"]), version=version)
                handled.add("default")

        for key, data in manifest.items():
            data_keypath = tuple([*keypath, key])
            obj = self.__manifest.get(key, None)
            if not obj and isinstance(data, dict) and "__meta__" in data:
                # Lookup object, use class first, then type
                cls = BaseSchema.__process_meta_section(data["__meta__"])
                if cls is BaseSchema and self.__default:
                    # Use default when BaseSchema is the class
                    obj = self.__default.copy(key=data_keypath)
                    self.__manifest[key] = obj
                elif cls:
                    # Create object and connect to schema
                    obj = cls()
                    obj.__parent = self
                    obj.__key = key
                    self.__manifest[key] = obj

            # Use default if it is available
            if not obj and self.__default:
                obj = self.__default.copy(key=data_keypath)
                self.__manifest[key] = obj

            if obj:
                if isinstance(obj, BaseSchema):
                    obj._from_dict(data, data_keypath, version=version, lazyload=lazyload.next)
                else:
                    obj._from_dict(data, data_keypath, version=version)
                handled.add(key)
            else:
                missing.add(key)

        return missing, set(self.__manifest.keys()).difference(handled)

    # Manifest methods
    @classmethod
    def from_manifest(cls,
                      filepath: Union[None, str] = None,
                      cfg: Union[None, Dict] = None,
                      lazyload: bool = True) -> "BaseSchema":
        '''
        Create a new schema based on the provided source files.

        The two arguments to this method are mutually exclusive.

        Args:
            filepath (path): Initial manifest.
            cfg (dict): Initial configuration dictionary.
        '''

        if not filepath and cfg is None:
            raise RuntimeError("filepath or dictionary is required")

        if filepath:
            cfg = BaseSchema._read_manifest(filepath)

        new_cls = None
        if "__meta__" in cfg:
            # Determine correct class
            new_cls = BaseSchema.__process_meta_section(cfg["__meta__"])
        if new_cls:
            schema = new_cls()
        else:
            schema = cls()

        if lazyload:
            do_lazyload = LazyLoad.ON
        else:
            do_lazyload = LazyLoad.OFF

        schema._from_dict(cfg, tuple(), lazyload=do_lazyload)

        return schema

    @staticmethod
    def __open_file(filepath: str, is_read: bool = True) -> TextIO:
        _, ext = os.path.splitext(filepath)
        if ext.lower() == ".gz":
            if not _has_gzip:
                raise RuntimeError("gzip is not available")
            return gzip.open(filepath, mode="rt" if is_read else "wt", encoding="utf-8")
        return open(filepath, mode="r" if is_read else "w", encoding="utf-8")

    def __format_key(self, *key: str):
        return f"[{','.join([*self._keypath, *key])}]"

    @staticmethod
    def _read_manifest(filepath: str) -> Dict:
        """
        Reads a manifest from disk and returns dictionary.

        Args:
            filename (path): Path to a manifest file to be loaded.
        """

        fin = BaseSchema.__open_file(filepath)
        try:
            manifest = json.loads(fin.read())
        finally:
            fin.close()

        return manifest

    def read_manifest(self, filepath: str) -> None:
        """
        Reads a manifest from disk and replaces the current data with the data in the file.

        Args:
            filename (path): Path to a manifest file to be loaded.

        Examples:
            >>> schema.read_manifest('mychip.json')
            Loads the file mychip.json into the current Schema object.
        """

        self._from_dict(BaseSchema._read_manifest(filepath), [])

    def write_manifest(self, filepath: str) -> None:
        '''
        Writes the manifest to a file.

        Args:
            filename (filepath): Output filepath.

        Examples:
            >>> schema.write_manifest('mydump.json')
            Dumps the current manifest into mydump.json
        '''

        fout = BaseSchema.__open_file(filepath, is_read=False)

        try:
            if _has_orjson:
                manifest_str = json.dumps(self.getdict(), option=json.OPT_INDENT_2).decode()
            else:
                manifest_str = json.dumps(self.getdict(), indent=2)
            fout.write(manifest_str)
        finally:
            fout.close()

    # Accessor methods
    def __search(self,
                 *keypath: str,
                 insert_defaults: bool = False,
                 use_default: bool = False,
                 require_leaf: bool = True,
                 complete_path: Optional[List[str]] = None,
                 elaborate_leaf: bool = True) -> Union["BaseSchema", Parameter]:

        if len(keypath) == 0:
            if require_leaf:
                raise KeyError
            else:
                if elaborate_leaf:
                    self.__ensure_lazy_elab()
                return self

        self.__ensure_lazy_elab()

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
                    if elaborate_leaf:
                        key_param.__ensure_lazy_elab()
                    return key_param
            return key_param.__search(*keypath[1:],
                                      insert_defaults=insert_defaults,
                                      use_default=use_default,
                                      require_leaf=require_leaf,
                                      complete_path=complete_path)
        elif len(keypath) != 1:
            # Key extends beyond parameter
            raise KeyError
        return key_param

    def get(self, *keypath: str, field: Optional[str] = 'value',
            step: Optional[str] = None, index: Optional[Union[int, str]] = None):
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
            insert_defaults = False
            if field == 'schema':
                require_leaf = False
                insert_defaults = True
            param = self.__search(
                *keypath,
                insert_defaults=insert_defaults,
                use_default=True,
                require_leaf=require_leaf)
            if field == 'schema':
                if isinstance(param, Parameter):
                    raise ValueError(f"{self.__format_key(*keypath)} is a complete keypath")
                self.__journal.record("get", keypath, field=field, step=step, index=index)
                param.__journal = self.__journal.get_child(*keypath)
                return param
        except KeyError:
            raise KeyError(f"{self.__format_key(*keypath)} is not a valid keypath")
        if field is None:
            return param

        try:
            get_ret = param.get(field, step=step, index=index)
            self.__journal.record("get", keypath, field=field, step=step, index=index)
            return get_ret
        except Exception as e:
            new_msg = f"error while accessing {self.__format_key(*keypath)}: {e.args[0]}"
            e.args = (new_msg, *e.args[1:])
            raise e

    def set(self, *args, field: str = 'value', clobber: bool = True,
            step: Optional[str] = None, index: Optional[Union[int, str]] = None) \
            -> Optional[Union[List[NodeValue], NodeValue]]:
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
            param: Parameter = self.__search(*keypath, insert_defaults=True)
        except KeyError:
            raise KeyError(f"{self.__format_key(*keypath)} is not a valid keypath")

        try:
            set_ret = param.set(value, field=field, clobber=clobber,
                                step=step, index=index)
            if set_ret:
                self.__journal.record("set", keypath, value=value, field=field,
                                      step=step, index=index)
                self.__process_active(param, set_ret)
            return set_ret
        except Exception as e:
            new_msg = f"error while setting {self.__format_key(*keypath)}: {e.args[0]}"
            e.args = (new_msg, *e.args[1:])
            raise e

    def add(self, *args, field: str = 'value',
            step: Optional[str] = None, index: Optional[Union[int, str]] = None) \
            -> Optional[Union[List[NodeValue], NodeValue]]:
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
            param: Parameter = self.__search(*keypath, insert_defaults=True)
        except KeyError:
            raise KeyError(f"{self.__format_key(*keypath)} is not a valid keypath")

        try:
            add_ret = param.add(value, field=field, step=step, index=index)
            if add_ret:
                self.__journal.record("add", keypath, value=value, field=field,
                                      step=step, index=index)
                self.__process_active(param, add_ret)
            return add_ret
        except Exception as e:
            new_msg = f"error while adding to {self.__format_key(*keypath)}: {e.args[0]}"
            e.args = (new_msg, *e.args[1:])
            raise e

    def unset(self, *keypath: str,
              step: Optional[str] = None,
              index: Optional[Union[int, str]] = None) -> None:
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
            raise KeyError(f"{self.__format_key(*keypath)} is not a valid keypath")

        try:
            param.unset(step=step, index=index)
            self.__journal.record("unset", keypath, step=step, index=index)
        except Exception as e:
            new_msg = f"error while unsetting {self.__format_key(*keypath)}: {e.args[0]}"
            e.args = (new_msg, *e.args[1:])
            raise e

    def remove(self, *keypath: str):
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
            raise KeyError(f"{self.__format_key(*keypath)} is not a valid keypath")

        if removal_key not in key_param.__manifest:
            return

        if not key_param.__default:
            return

        if any([key_param.get(*key, field='lock') for key in key_param.allkeys()]):
            return

        del key_param.__manifest[removal_key]
        self.__journal.record("remove", keypath)

    def valid(self, *keypath: str, default_valid: bool = False,
              check_complete: bool = False) -> bool:
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

        if param is None:
            return False

        if check_complete:
            return isinstance(param, Parameter)
        return True

    def getkeys(self, *keypath: str) -> Tuple[str, ...]:
        """
        Returns a tuple of schema dictionary keys.

        Searches the schema for the keypath provided and returns a list of
        keys found, excluding the generic 'default' key.

        Args:
            keypath (list of str): Keypath to get keys for.

        Returns:
            tuple of keys found for the keypath provided.

        Examples:
            >>> keylist = schema.getkeys('pdk')
            Returns all keys for the [pdk] keypath.
        """
        try:
            key_param = self.__search(*keypath, require_leaf=False)
        except KeyError:
            raise KeyError(f"{self.__format_key(*keypath)} is not a valid keypath")

        if isinstance(key_param, Parameter):
            return tuple()

        return tuple(sorted(key_param.__manifest.keys()))

    def allkeys(self, *keypath: str, include_default: bool = True) -> Set[Tuple[str, ...]]:
        '''
        Returns all keypaths in the schema as a set of tuples.

        Arg:
            keypath (list of str): Keypath prefix to search under. The
                returned keypaths do not include the prefix.
        '''
        try:
            key_param = self.__search(*keypath, require_leaf=False)
        except KeyError:
            return set()

        if isinstance(key_param, Parameter):
            return set()

        def add(keys: List[Tuple[str, ...]],
                key: str,
                item: Union["BaseSchema", Parameter]) -> None:
            if isinstance(item, Parameter):
                keys.append((key,))
            else:
                for subkeypath in item.allkeys(include_default=include_default):
                    keys.append((key, *subkeypath))

        keys = []
        if include_default and key_param.__default:
            add(keys, "default", key_param.__default)
        for key, item in key_param.__manifest.items():
            add(keys, key, item)
        return set(keys)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the type data for getdict
        """

        return "BaseSchema"

    def _getdict_meta(self) -> Dict[str, Optional[Union[str, int, float]]]:
        """
        Returns the meta data for getdict
        """

        return {}

    def getdict(self, *keypath: str, include_default: bool = True,
                values_only: bool = False) -> Dict:
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
        try:
            if not values_only and include_default:
                key_param = self.__search(*keypath, require_leaf=False, elaborate_leaf=False)

                if isinstance(key_param, Parameter):
                    return key_param.getdict(include_default=include_default,
                                             values_only=values_only)

                if key_param.__lazy:
                    return key_param.__lazy[1]
            else:
                key_param = self.__search(*keypath, require_leaf=False)
        except KeyError:
            return {}

        if isinstance(key_param, Parameter):
            return key_param.getdict(include_default=include_default, values_only=values_only)

        manifest = {}
        if include_default and key_param.__default:
            manifest_dict = key_param.__default.getdict(include_default=include_default,
                                                        values_only=values_only)
            if manifest_dict or not values_only:
                manifest["default"] = manifest_dict
        for key, item in key_param.__manifest.items():
            manifest_dict = item.getdict(include_default=include_default,
                                         values_only=values_only)
            if manifest_dict or not values_only:
                manifest[key] = manifest_dict

        if not values_only and key_param.__journal.has_journaling():
            manifest["__journal__"] = key_param.__journal.get()

        if not values_only and key_param.__class__ is not BaseSchema:
            manifest["__meta__"] = {}

            try:
                cls_meta = key_param._getdict_meta()
                manifest["__meta__"].update(cls_meta)
            except NotImplementedError:
                pass

            manifest["__meta__"]["class"] = \
                f"{key_param.__class__.__module__}/{key_param.__class__.__name__}"
            try:
                manifest["__meta__"]["sctype"] = key_param._getdict_type()
            except NotImplementedError:
                pass

        return manifest

    # Utility functions
    def copy(self, key: Optional[Tuple[str, ...]] = None) -> "BaseSchema":
        """
        Returns a copy of this schema.

        Args:
            key (list of str): keypath to this schema
        """

        parent = self.__parent
        self.__parent = None
        schema_copy = copy.deepcopy(self)
        self.__parent = parent
        schema_copy.__parent = self.__parent

        if key:
            schema_copy.__key = key[-1]

        return schema_copy

    def _find_files_search_paths(self, key: str,
                                 step: Optional[str],
                                 index: Optional[Union[int, str]]) -> List[str]:
        """
        Returns a list of paths to search during find files.

        Args:
            key (str): final component of keypath
            step (str): Step name.
            index (str): Index name.
        """
        return []

    def _find_files_dataroot_resolvers(self, resolvers: bool = False) \
            -> Dict[str, Union[str, Callable]]:
        """
        Returns a dictionary of path resolvers data directory handling for find_files

        Args:
            resolvers (bool, optional): Returns the resolvers instead of callables

        Returns:
            dictionary of str to resolver mapping
        """
        if self.__is_root:
            return {}
        return self.__parent._find_files_dataroot_resolvers(resolvers=resolvers)

    def _find_files(self, *keypath: str, missing_ok: bool = False,
                    step: Optional[str] = None, index: Optional[Union[int, str]] = None,
                    dataroots: Optional[Dict[str, Union[str, Callable]]] = None,
                    collection_dir: Optional[str] = None,
                    cwd: Optional[str] = None) \
            -> Union[Optional[str], List[Optional[str]], Set[Optional[str]]]:
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
            dataroots (dict of resolvers): dirctionary of path resolvers for dataroot
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
            >>> schema.find_files('input', 'verilog')
            Returns a list of absolute paths to source files, as specified in
            the schema.
        """
        return self.__find_files_or_hash(
            *keypath, missing_ok=missing_ok,
            step=step, index=index,
            dataroots=dataroots,
            collection_dir=collection_dir,
            cwd=cwd, hash=False)

    def __find_files_or_hash(self, *keypath: str, missing_ok: bool = False,
                             step: Optional[str] = None, index: Optional[Union[int, str]] = None,
                             dataroots: Optional[Dict[str, Union[str, Callable]]] = None,
                             collection_dir: Optional[str] = None,
                             cwd: Optional[str] = None,
                             hash: bool = False) \
            -> Union[Optional[str], List[Optional[str]], Set[Optional[str]]]:
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
            dataroots (dict of resolvers): dirctionary of path resolvers for dataroot
                paths, these can either be a path or a callable function
            collection_dir (path): optional path to a collections directory
            cwd (path): optional path to current working directory, this will default
                to os.getcwd() if not provided.
            hash (bool): hash the files insteasd of getting the paths

        Returns:
            If keys points to a scalar entry, returns an absolute path to that
            file/directory, or None if not found. It keys points to a list
            entry, returns a list of either the absolute paths or None for each
            entry, depending on whether it is found.

        Examples:
            >>> schema.find_files('input', 'verilog')
            Returns a list of absolute paths to source files, as specified in
            the schema.
        """

        base_schema: BaseSchema = self.get(*keypath[0:-1], field="schema")

        param: Parameter = base_schema.get(keypath[-1], field=None)
        paramtype: str = param.get(field='type')
        if 'file' not in paramtype and 'dir' not in paramtype:
            raise TypeError(
                f'Cannot find files on {self.__format_key(*keypath)}, must be a path type')

        hashalgo: Optional[str] = None
        if hash:
            hashalgo = param.get(field="hashalgo")

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

        if dataroots is None:
            dataroots = base_schema._find_files_dataroot_resolvers()

        resolved_paths = []
        root_search_paths = base_schema._find_files_search_paths(keypath[-1], step, index)
        for path in paths:
            search_paths = root_search_paths.copy()

            dataroot: Optional[str] = path.get(field="dataroot")
            dataroot_except: Optional[Exception] = None
            if dataroot:
                if dataroot not in dataroots:
                    raise ValueError(f"Resolver for {dataroot} not provided: "
                                     f"{self.__format_key(*keypath)}")
                dataroot_path = dataroots[dataroot]
                if isinstance(dataroot_path, str):
                    search_paths.append(os.path.abspath(dataroot_path))
                elif callable(dataroot_path):
                    try:
                        search_paths.append(dataroot_path())
                    except Exception as e:
                        dataroot_except = e
                else:
                    raise TypeError(f"Resolver for {dataroot} is not a recognized type: "
                                    f"{self.__format_key(*keypath)}")
            else:
                if cwd:
                    search_paths.append(os.path.abspath(cwd))

            try:
                if hash:
                    resolved = path.hash(hashalgo,
                                         search=search_paths,
                                         collection_dir=collection_dir)
                else:
                    resolved = path.resolve_path(search=search_paths,
                                                 collection_dir=collection_dir)
            except FileNotFoundError:
                resolved = None
                if not missing_ok:
                    report_paths = ", ".join(search_paths)
                    if dataroot:
                        if dataroot_except:
                            raise FileNotFoundError(
                                f"Dataroot {dataroot} not found: {dataroot_except}") \
                                    from dataroot_except
                        raise FileNotFoundError(
                            f'Could not find "{path.get()}" in {dataroot} '
                            f'{self.__format_key(*keypath)}: {report_paths}')
                    else:
                        raise FileNotFoundError(
                            f'Could not find "{path.get()}" {self.__format_key(*keypath)}: '
                            f'{report_paths}')
            resolved_paths.append(resolved)

        if not is_list:
            if not resolved_paths:
                return None
            return resolved_paths[0]
        return resolved_paths

    def _check_filepaths(self, ignore_keys: Optional[Iterable[Tuple[str, ...]]] = None,
                         logger: Optional[logging.Logger] = None,
                         dataroots: Optional[Dict[str, Union[str, Callable]]] = None,
                         collection_dir: Optional[str] = None,
                         cwd: Optional[str] = None) -> bool:
        '''
        Verifies that paths to all files in manifest are valid.

        Args:
            ignore_keys (list of keypaths): list of keypaths to ignore while checking
            logger (:class:`logging.Logger`): optional logger to use to report errors
            dataroots (dict of resolvers): dirctionary of path resolvers for dataroot
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

            param: Parameter = self.get(*keypath, field=None)
            paramtype: str = param.get(field='type')

            if 'file' not in paramtype and 'dir' not in paramtype:
                continue

            for check_files, step, index in param.getvalues():
                if not check_files:
                    # nothing set so continue
                    continue

                found_files = BaseSchema._find_files(
                    self, *keypath, missing_ok=True, step=step, index=index,
                    dataroots=dataroots, collection_dir=collection_dir, cwd=cwd)

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

                            name = ""
                            if hasattr(self, "name"):
                                name = f"({self.name}) "

                            logger.error(f"Parameter {name}"
                                         f"{self.__format_key(*keypath)}{node_indicator} "
                                         f"path {check_file} is invalid")

        return not error

    def _hash_files(self, *keypath, missing_ok: bool = False,
                    step: Optional[str] = None, index: Optional[Union[int, str]] = None,
                    dataroots: Optional[Dict[str, Union[str, Callable]]] = None,
                    collection_dir: Optional[str] = None,
                    cwd: Optional[str] = None):
        '''Generates hash values for a list of parameter files.

        Generates a hash value for each file found in the keypath. If existing
        hash values are stored, this method will compare hashes and trigger an
        error if there's a mismatch. If the update variable is True, the
        computed hash values are recorded in the 'filehash' field of the
        parameter, following the order dictated by the files within the 'value'
        parameter field.

        Files are located using the find_files() function.

        The file hash calculation is performed based on the 'algo' setting.
        Supported algorithms include SHA1, SHA224, SHA256, SHA384, SHA512,
        and MD5.

        Args:
            *keypath(str): Keypath to parameter.
            missing_ok (bool): If True, silently return None when files aren't
                found. If False, print an error and set the error flag.
            step (str): Step name to access for parameters that may be specified
                on a per-node basis.
            index (str): Index name to access for parameters that may be specified
                on a per-node basis.
            dataroots (dict of resolvers): dirctionary of path resolvers for dataroot
                paths, these can either be a path or a callable function
            collection_dir (path): optional path to a collections directory
            cwd (path): optional path to current working directory, this will default
                to os.getcwd() if not provided.

        Returns:
            A list of hash values.

        Examples:
            >>> hashlist = hash_files('input', 'rtl', 'verilog')
            Computes, stores, and returns hashes of files in :keypath:`input, rtl, verilog`.
        '''
        return self.__find_files_or_hash(
            *keypath, missing_ok=missing_ok,
            step=step, index=index,
            dataroots=dataroots,
            collection_dir=collection_dir,
            cwd=cwd, hash=True)

    def _parent(self, root: bool = False) -> "BaseSchema":
        '''
        Returns the parent of this schema section, if root is true the root parent
        will be returned.

        Args:
            root (bool): if true, returns the root of the schemas.
        '''
        if self.__is_root:
            return self

        if not root:
            return self.__parent
        return self.__parent._parent(root=root)

    @contextlib.contextmanager
    def _active(self, **kwargs):
        '''
        Use this context to temporarily set additional fields in :meth:`.set` and :meth:`.add`.
        Additional fields can be specified which can be accessed by :meth:`._get_active`.

        Args:
            kwargs (dict of str): keyword arguments that are used for setting values

        Example:
            >>> with schema._active(dataroot="lambdalib"):
            ...     schema.set("file", "top.v")
            Sets the file to top.v and associates lambdalib as the dataroot.
        '''

        if self.__active is None:
            orig_active = None
            self.__active = {}
        else:
            orig_active = self.__active.copy()

        self.__active.update(kwargs)

        try:
            yield
        finally:
            self.__active = orig_active

    def _get_active(self, field: str, defvalue=None):
        '''
        Get the value of a specific field.

        Args:
            field (str): if None, return the current active dictionary,
                         otherwise the value, if the field is not present, defvalue is returned.
            defvalue (any): value to return if the field is not present.
        '''
        actives = self.__get_active()
        if actives is None:
            return defvalue

        if field is None:
            return actives

        return actives.get(field, defvalue)

    def __get_active(self) -> Optional[Dict[str, Any]]:
        '''
        Get the actives this point in the schema
        '''
        schemas: List["BaseSchema"] = [self]

        root = self._parent(root=True)
        curr = schemas[-1]
        while curr is not root:
            schemas.append(curr._parent())
            curr = schemas[-1]

        active = {}
        for schema in reversed(schemas):
            if schema.__active:
                active.update(schema.__active)
        if not active:
            return None
        return active

    def __process_active(self, param: Parameter,
                         nodevalues: Optional[Union[List[NodeValue],
                                                    Set[NodeValue],
                                                    Tuple[NodeValue, ...],
                                                    NodeValue]]) -> None:
        actives = self.__get_active()
        if actives is None:
            return

        if not isinstance(nodevalues, (list, set, tuple)):
            # Make everything a list
            nodevalues = [nodevalues]

        if not all([isinstance(v, NodeValue) for v in nodevalues]):
            nodevalues = []
            nodevalues_fields = []
        else:
            nodevalues_fields = nodevalues[0].fields

        key_fields = ("copy", "lock")

        for field, value in actives.items():
            if field in key_fields:
                param.set(value, field=field)
                continue

            if field not in nodevalues_fields:
                continue

            for param in nodevalues:
                param.set(value, field=field)

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from .docs.utils import build_section_with_target, build_schema_value_table, get_key_ref, \
            parse_rst
        from docutils import nodes

        if not key_offset:
            key_offset = tuple()

        if detailed:
            sections = []
            if not self.__class__.__module__.startswith("siliconcompiler.schema."):
                cls_info = nodes.paragraph()
                parse_rst(
                    doc.state,
                    f"Class :class:`{self.__class__.__name__} "
                    f"<{self.__class__.__module__}.{self.__class__.__name__}>`",
                    cls_info,
                    __file__)
                sections.append(cls_info)
            if self.__default:
                if isinstance(self.__default, Parameter):
                    sections.extend(Parameter._generate_doc(self.__default, doc))
                else:
                    sections.extend(BaseSchema._generate_doc(self.__default,
                                                             doc,
                                                             ref_root=ref_root,
                                                             key_offset=key_offset,
                                                             detailed=detailed))
            for name, obj in self.__manifest.items():
                root = self._parent(root=True)

                section = build_section_with_target(name,
                                                    get_key_ref(list(self._keypath) + [name],
                                                                ref=root),
                                                    doc.state.document)
                if isinstance(obj, Parameter):
                    for n in Parameter._generate_doc(obj, doc):
                        section += n
                else:
                    for n in BaseSchema._generate_doc(obj,
                                                      doc,
                                                      ref_root=ref_root,
                                                      key_offset=key_offset,
                                                      detailed=detailed):
                        section += n
                sections.append(section)

            # Sort all sections alphabetically by title. We may also have nodes
            # in this list that aren't sections if `schema` has a 'default'
            # entry that's a leaf. In this case, we sort this as an empty string
            # in order to put this node at the beginning of the list.
            return sorted(sections, key=lambda s: s[0][0] if isinstance(s, nodes.section) else '')
        else:
            params = {}
            for key in self.allkeys(include_default=False):
                params[key] = self.get(*key, field=None)
            table = build_schema_value_table(params, doc.env.docname, (*key_offset, *self._keypath))
            if table:
                return table
            return None
