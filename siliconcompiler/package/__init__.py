"""
This module defines the core path resolution system for SiliconCompiler packages.

It provides a flexible mechanism to locate data sources, whether they are on
the local filesystem, remote servers, or part of a Python package. The system
is designed to be extensible, allowing new resolver types to be added as plugins.
It also includes robust caching and locking mechanisms for handling remote data
efficiently and safely in multi-process and multi-threaded environments.
"""
import contextlib
import functools
import hashlib
import importlib
import json
import logging
import os
import random
import re
import shutil
import time
import threading
import uuid

import os.path

from typing import Optional, List, Dict, Type, Union, TYPE_CHECKING, ClassVar

from fasteners import InterProcessLock
from importlib.metadata import distributions, distribution
from pathlib import Path
from urllib import parse as url_parse

from siliconcompiler.utils import get_plugins, default_cache_dir
from siliconcompiler.utils.paths import cwdirsafe

if TYPE_CHECKING:
    from siliconcompiler.project import Project
    from siliconcompiler.schema_support.pathschema import PathSchema
    from siliconcompiler.schema import BaseSchema


class Resolver:
    """
    Abstract base class for all data source resolvers.

    This class defines the common interface for locating and accessing data
    from various sources. It includes a caching mechanism to avoid redundant
    resolutions within a single run.

    Attributes:
        name (str): The name of the data package being resolved.
        root (object): The root object (typically a Project) providing context,
            such as environment variables and the working directory.
        source (str): The URI or path specifying the data source.
        reference (str): A version, commit hash, or tag for remote sources.
    """
    _RESOLVERS_LOCK: ClassVar[threading.Lock] = threading.Lock()
    _RESOLVERS: ClassVar[Dict[str, Type["Resolver"]]] = {}
    __STORAGE: str = "__Resolver_cache_id"

    __CACHE_LOCK: ClassVar[threading.Lock] = threading.Lock()
    __CACHE: ClassVar[Dict[str, Dict[str, str]]] = {}

    def __init__(self, name: str,
                 root: Optional[Union["Project", "BaseSchema"]],
                 source: str,
                 reference: Optional[str] = None):
        """
        Initializes the Resolver.
        """
        self.__name = name
        self.__root = root
        self.__source = source
        self.__reference = reference
        self.__changed = False
        self.__cacheid = None

        if self.__root and hasattr(self.__root, "logger"):
            self.__logger = self.__root.logger.getChild(f"resolver-{self.name}")
        else:
            self.__logger = logging.getLogger(f"resolver-{self.name}")

    @staticmethod
    def populate_resolvers() -> None:
        """
        Scans for and registers all available resolver plugins.

        This method populates the internal `_RESOLVERS` dictionary with both
        built-in resolvers (file, key, python) and any resolvers provided
        by external plugins.
        """
        with Resolver._RESOLVERS_LOCK:
            Resolver._RESOLVERS.clear()

            Resolver._RESOLVERS.update({
                "": FileResolver,
                "file": FileResolver,
                "key": KeyPathResolver,
                "python": PythonPathResolver
            })

            for resolver in get_plugins("path_resolver"):
                Resolver._RESOLVERS.update(resolver())

    @staticmethod
    def find_resolver(source: str) -> Type["Resolver"]:
        """
        Finds the appropriate resolver class for a given source URI.

        Args:
            source (str): The source URI (e.g., 'file:///path/to/file', 'git://...').

        Returns:
            Resolver: The resolver class capable of handling the source.

        Raises:
            ValueError: If no suitable resolver is found for the URI scheme.
        """
        if os.path.isabs(source):
            return FileResolver

        if not Resolver._RESOLVERS:
            Resolver.populate_resolvers()

        url = url_parse.urlparse(source)
        with Resolver._RESOLVERS_LOCK:
            if url.scheme in Resolver._RESOLVERS:
                return Resolver._RESOLVERS[url.scheme]

        raise ValueError(f"Source URI '{source}' is not supported")

    @property
    def name(self) -> str:
        """The name of the data package being resolved."""
        return self.__name

    @property
    def root(self) -> Optional[Union["Project", "BaseSchema"]]:
        """The root object (e.g., Project) providing context."""
        return self.__root

    @property
    def logger(self) -> logging.Logger:
        """The logger instance for this resolver."""
        return self.__logger

    @property
    def source(self) -> str:
        """The URI or path specifying the data source."""
        return self.__source

    @property
    def reference(self) -> Union[None, str]:
        """A version, commit hash, or tag for the source."""
        return self.__reference

    @property
    def urlparse(self) -> url_parse.ParseResult:
        """The parsed URL of the source after environment variable expansion."""
        return url_parse.urlparse(self.__resolve_env(self.source))

    @property
    def urlscheme(self) -> str:
        """The scheme of the source URL (e.g., 'file', 'git')."""
        return self.urlparse.scheme

    @property
    def urlpath(self) -> str:
        """The path component of the source URL."""
        return self.urlparse.netloc

    @property
    def changed(self) -> bool:
        """
        Indicates if the resolved data has changed (e.g., was newly fetched).

        This flag is reset to False after being read.
        """
        change = self.__changed
        self.__changed = False
        return change

    @property
    def cache_id(self) -> str:
        """A unique ID for this resolver instance, used for caching."""
        if self.__cacheid is None:
            hash_obj = hashlib.sha1()
            hash_obj.update(self.__source.encode())
            if self.__reference:
                hash_obj.update(self.__reference.encode())
            else:
                hash_obj.update("".encode())

            self.__cacheid = hash_obj.hexdigest()
        return self.__cacheid

    def set_changed(self):
        """Marks the resolved data as having been changed."""
        self.__changed = True

    def resolve(self) -> Union[Path, str]:
        """
        Abstract method to perform the actual data resolution.

        Subclasses must implement this method to locate or fetch the data
        and return its local path.
        """
        raise NotImplementedError("child class must implement this")

    @staticmethod
    def __get_root_id(root: Union["Project", "BaseSchema"]) -> str:
        """Generates or retrieves a unique ID for a root object."""
        if not getattr(root, Resolver.__STORAGE, None):
            setattr(root, Resolver.__STORAGE, uuid.uuid4().hex)
        return getattr(root, Resolver.__STORAGE)

    @staticmethod
    def get_cache(root: Optional[Union["Project", "BaseSchema"]], name: Optional[str] = None) \
            -> Union[None, str, Dict[str, str]]:
        """
        Gets a cached path for a given root object and resolver name.

        Args:
            root: The root object (e.g., Project).
            name (str, optional): The name of the resolver cache to retrieve.
                If None, returns a copy of the entire cache for the root.

        Returns:
            str or dict or None: The cached path, a copy of the cache, or None.
        """
        if root is None:
            return None

        with Resolver.__CACHE_LOCK:
            root_id = Resolver.__get_root_id(root)
            if root_id not in Resolver.__CACHE:
                Resolver.__CACHE[root_id] = {}

            if name:
                return Resolver.__CACHE[root_id].get(name, None)

            return Resolver.__CACHE[root_id].copy()

    @staticmethod
    def set_cache(root: Optional[Union["Project", "BaseSchema"]],
                  name: str,
                  path: Union[Path, str]) -> None:
        """
        Sets a cached path for a given root object and resolver name.

        Args:
            root: The root object (e.g., Project).
            name (str): The name of the resolver cache to set.
            path (str): The path to cache.
        """
        if root is None:
            return

        with Resolver.__CACHE_LOCK:
            root_id = Resolver.__get_root_id(root)
            if root_id not in Resolver.__CACHE:
                Resolver.__CACHE[root_id] = {}
            Resolver.__CACHE[root_id][name] = str(path)

    @staticmethod
    def reset_cache(root: Optional[Union["Project", "BaseSchema"]]) -> None:
        """
        Resets the entire cache for a given root object.

        Args:
            root: The root object whose cache will be cleared.
        """
        if root is None:
            return

        with Resolver.__CACHE_LOCK:
            root_id = Resolver.__get_root_id(root)
            if root_id in Resolver.__CACHE:
                del Resolver.__CACHE[root_id]

    def get_path(self) -> str:
        """
        Resolves the data source and returns its local path.

        This method first checks the in-memory cache. If not found, it calls
        the `resolve()` method and caches the result.

        Returns:
            str: The absolute path to the resolved data on the local filesystem.

        Raises:
            FileNotFoundError: If the resolved path does not exist.
        """
        cache_path: Optional[str] = Resolver.get_cache(self.__root, self.cache_id)
        if cache_path:
            return cache_path

        path = self.resolve()
        if not os.path.exists(path):
            raise FileNotFoundError(f"Unable to locate '{self.name}' at {path}")

        if self.changed:
            self.logger.info(f'Saved {self.name} data to {path}')
        else:
            self.logger.info(f'Found {self.name} data at {path}')

        Resolver.set_cache(self.__root, self.cache_id, path)
        return str(path)

    def __resolve_env(self, path: str) -> str:
        """Expands environment variables and user home directory in a path."""
        env_save = os.environ.copy()

        if self.root:
            schema_env = {}
            if self.root.valid("option", "env"):
                for env in self.root.getkeys('option', 'env'):
                    schema_env[env] = self.root.get('option', 'env', env)
            os.environ.update(schema_env)

        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        os.environ.clear()
        os.environ.update(env_save)
        return path


class RemoteResolver(Resolver):
    """
    An abstract base class for resolvers that fetch data from remote sources.

    This class extends `Resolver` with functionality for managing a persistent
    on-disk cache in `~/.sc/cache` or a user-defined location. It implements
    both thread-safe and process-safe locking to prevent race conditions when
    multiple SC instances try to download the same resource simultaneously.
    """
    _CACHE_LOCKS = {}
    _CACHE_LOCK = threading.Lock()

    def __init__(self, name: str,
                 root: Optional[Union["Project", "BaseSchema"]],
                 source: str,
                 reference: Optional[str] = None):
        if reference is None:
            raise ValueError(f'A reference (e.g., version, commit) is required for {name}')

        super().__init__(name, root, source, reference)

        # Wait a maximum of 10 minutes for other processes to finish
        self.__max_lock_wait: int = 60 * 10

    @property
    def timeout(self) -> int:
        """The maximum time in seconds to wait for a lock."""
        return self.__max_lock_wait

    def set_timeout(self, value: int) -> None:
        """Sets the maximum time in seconds to wait for a lock."""
        self.__max_lock_wait = value

    @staticmethod
    def determine_cache_dir(root: Optional[Union["Project", "BaseSchema"]]) -> Path:
        """
        Determines the directory for the on-disk cache.

        The location is determined by ['option', 'cachedir'] if set, otherwise
        it defaults to `~/.sc/cache`.

        Args:
            root: The root Project object.

        Returns:
            Path: The path to the cache directory.
        """
        default_path = default_cache_dir()
        if not root:
            return Path(default_path)

        path = None
        if root.valid('option', 'cachedir'):
            path = root.get('option', 'cachedir')
            if path:
                path = root.find_files('option', 'cachedir', missing_ok=True)
                if not path:
                    path = os.path.join(cwdirsafe(root), root.get('option', 'cachedir'))
        if not path:
            path = default_path

        return Path(path)

    @property
    def cache_dir(self) -> Path:
        """The directory for the on-disk cache."""
        return RemoteResolver.determine_cache_dir(self.root)

    @property
    def cache_name(self) -> str:
        """A unique name for the cached data directory."""
        return f"{self.name}-{self.reference[0:16]}-{self.cache_id[0:16]}"

    @property
    def cache_path(self) -> Path:
        """The full path to the cached data directory."""
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        return self.cache_dir / self.cache_name

    @property
    def lock_file(self) -> Path:
        """The path to the file used for inter-process locking."""
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        return self.cache_dir / f"{self.cache_name}.lock"

    @property
    def sc_lock_file(self) -> Path:
        """
        The path to a secondary lock file used as a fallback mechanism.
        """
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        return self.cache_dir / f"{self.cache_name}.sc_lock"

    def thread_lock(self) -> threading.Lock:
        """Gets a threading.Lock specific to this resolver instance."""
        with RemoteResolver._CACHE_LOCK:
            if self.name not in RemoteResolver._CACHE_LOCKS:
                RemoteResolver._CACHE_LOCKS[self.name] = threading.Lock()
            return RemoteResolver._CACHE_LOCKS[self.name]

    @contextlib.contextmanager
    def __thread_lock(self):
        """A context manager for acquiring the thread lock with a timeout."""
        lock = self.thread_lock()
        lock_acquired = False
        try:
            timeout = self.timeout
            while timeout > 0:
                if lock.acquire_lock(timeout=1):
                    lock_acquired = True
                    break
                sleep_time = random.randint(1, max(1, int(timeout / 10)))
                timeout -= sleep_time + 1
                time.sleep(sleep_time)
            if lock_acquired:
                yield
        finally:
            if lock.locked():
                lock.release()

        if not lock_acquired:
            raise RuntimeError(f'Failed to access {self.cache_path}. '
                               f'Another thread is currently holding the lock.')

    @contextlib.contextmanager
    def __file_lock(self):
        """A context manager for acquiring the inter-process file lock."""
        data_path_lock = InterProcessLock(self.lock_file)
        lock_acquired = False
        sc_data_path_lock = None
        try:
            try:
                lock_acquired = data_path_lock.acquire(timeout=self.timeout)
            except (OSError, RuntimeError):
                if not lock_acquired:
                    sc_data_path_lock = Path(self.sc_lock_file)
                    max_seconds = self.timeout
                    while sc_data_path_lock.exists():
                        if max_seconds == 0:
                            raise RuntimeError(f'Failed to access {self.cache_path}. '
                                               f'Lock {sc_data_path_lock} still exists.')
                        time.sleep(1)
                        max_seconds -= 1
                    sc_data_path_lock.touch()
                    lock_acquired = True
            if lock_acquired:
                yield
        finally:
            if lock_acquired:
                if data_path_lock.acquired:
                    data_path_lock.release()
                if sc_data_path_lock:
                    sc_data_path_lock.unlink(missing_ok=True)

        if not lock_acquired:
            raise RuntimeError(f'Failed to access {self.cache_path}. '
                               f'{self.lock_file} is still locked. If this is a mistake, '
                               'please delete the lock file.')

    @contextlib.contextmanager
    def lock(self):
        """
        A context manager that acquires both the thread and file locks.

        This ensures that only one thread in one process can access the cache
        for a specific resource at a time.
        """
        with self.__thread_lock():
            with self.__file_lock():
                yield

    def resolve_remote(self) -> None:
        """Abstract method to fetch the remote data."""
        raise NotImplementedError("child class must implement this")

    def check_cache(self) -> bool:
        """
        Abstract method to check if the on-disk cache is valid.

        Returns:
            bool: True if the cache is valid, False otherwise.
        """
        raise NotImplementedError("child class must implement this")

    def resolve(self) -> Union[str, Path]:
        """
        Resolves the remote data, using the on-disk cache if possible.

        This method acquires locks, checks the cache validity, and calls
        `resolve_remote()` to fetch the data if the cache is missing or invalid.

        Returns:
            Path: The path to the locally cached data.
        """
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except OSError:
                # Can't create directory, return path and let it fail later
                return self.cache_path

        if not os.access(self.cache_dir, os.W_OK):
            # Can't write to directory, assume cache is valid if it exists
            return self.cache_path

        with self.lock():
            if self.check_cache():
                return self.cache_path

            try:
                self.resolve_remote()
            except BaseException as e:
                # Exception occurred, so need to cleanup
                try:
                    shutil.rmtree(self.cache_path)
                except BaseException as cleane:
                    self.logger.error(f"Exception occurred during cleanup: {cleane} "
                                      f"({cleane.__class__.__name__})")
                raise e from None

            self.set_changed()
            return self.cache_path


class FileResolver(Resolver):
    """
    A resolver for local file system paths.

    It handles both absolute paths and paths relative to the project's CWD.
    It normalizes the source string to a `file://` URI.
    """

    def __init__(self, name: str, root: "Project", source: str, reference: Optional[str] = None):
        if source.startswith("file://"):
            source = source[7:]
        if source[0] != "$" and not os.path.isabs(source):
            source = os.path.join(cwdirsafe(root), source)

        super().__init__(name, root, f"file://{source}", None)

    @property
    def urlpath(self) -> str:
        """The absolute file path, stripped of the 'file://' prefix."""
        # Rebuild URL and remove scheme prefix
        return self.urlparse.geturl()[7:]

    def resolve(self) -> str:
        """Returns the absolute path to the file."""
        path = self.urlpath
        if path and path[0] == "$":
            return path
        return os.path.abspath(path)


class PythonPathResolver(Resolver):
    """
    A resolver for locating installed Python packages.

    This resolver uses Python's import machinery to find the installation
    directory of a given Python module. It also includes helper methods to
    determine if a package is installed in "editable" mode.
    """

    def __init__(self, name: str, root: "Project", source: str, reference: Optional[str] = None):
        super().__init__(name, root, source, None)

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_python_module_mapping() -> Dict[str, List[str]]:
        """
        Creates a mapping from importable module names to their distribution names.

        This is used to find the distribution package that provides a given module.

        Returns:
            dict: A dictionary mapping module names to a list of distribution names.
        """
        mapping = {}

        for dist in distributions():
            dist_name = getattr(dist, 'name', None)
            if not dist_name:
                metadata = dist.read_text('METADATA')
                if metadata:
                    find_name = re.compile(r'Name: (.*)')
                    for data in metadata.splitlines():
                        group = find_name.findall(data)
                        if group:
                            dist_name = group[0]
                            break

            if not dist_name:
                continue

            provides = dist.read_text('top_level.txt')
            if provides:
                for module in provides.split():
                    mapping.setdefault(module, []).append(dist_name)

        return mapping

    @staticmethod
    def is_python_module_editable(module_name: str) -> bool:
        """
        Checks if a Python module is installed in "editable" mode.

        Args:
            module_name (str): The name of the Python module to check.

        Returns:
            bool: True if the module is installed in editable mode, False otherwise.
        """
        dist_map = PythonPathResolver.get_python_module_mapping()
        if module_name not in dist_map:
            return False
        dist_name = dist_map[module_name][0]

        is_editable = False
        dist_obj = distribution(dist_name)
        if not dist_obj or not dist_obj.files:
            return False

        for f in dist_obj.files:
            if f.name == 'direct_url.json':
                info = None
                with open(f.locate(), 'r') as fp:
                    info = json.load(fp)

                if "dir_info" in info:
                    is_editable = info["dir_info"].get("editable", False)

        return is_editable

    @staticmethod
    def set_dataroot(root: "PathSchema",
                     package_name: str,
                     python_module: str,
                     alternative_path: str,
                     alternative_ref: Optional[str] = None,
                     python_module_path_append: Optional[str] = None):
        """
        Helper to conditionally set a dataroot to a Python module or a fallback path.
        """
        # check if installed in an editable state
        if PythonPathResolver.is_python_module_editable(python_module):
            path = f"python://{python_module}"
            if python_module_path_append:
                py_path = PythonPathResolver(python_module, root, path).resolve()
                path = os.path.abspath(os.path.join(py_path, python_module_path_append))
            ref = None
        else:
            path = alternative_path
            ref = alternative_ref

        root.set_dataroot(package_name, path=path, tag=ref)

    def resolve(self) -> str:
        """
        Resolves the path to the specified Python module.

        Returns:
            str: The absolute path to the module's directory.
        """
        module = importlib.import_module(self.urlpath)
        python_path = os.path.dirname(module.__file__)
        return os.path.abspath(python_path)


class KeyPathResolver(Resolver):
    """
    A resolver for finding file paths stored within the project schema itself.

    This resolver takes a keypath (e.g., 'tool,openroad,exe') and uses the
    `find_files` method of the root project object to locate the corresponding file.
    """

    def __init__(self, name: str, root: "Project", source: str, reference: Optional[str] = None):
        super().__init__(name, root, source, None)

    def resolve(self) -> str:
        """
        Resolves the path by looking up the keypath in the project schema.

        Returns:
            str: The file path found in the schema.

        Raises:
            RuntimeError: If the resolver does not have a root project object defined.
        """
        if not self.root:
            raise RuntimeError(f"A root schema has not been defined for '{self.name}'")

        key = self.urlpath.split(",")
        if self.root.get(*key, field='pernode').is_never():
            paths = self.root.find_files(*key)
        else:
            paths = self.root.find_files(*key,
                                         step=self.root.get('arg', 'step'),
                                         index=self.root.get('arg', 'index'))

        if isinstance(paths, list):
            return paths[0]
        return paths
