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
import site
import shutil
import stat
import time
import threading

import os.path

from typing import Optional, List, Dict, Type, Union, TYPE_CHECKING

from fasteners import InterProcessLock
from importlib.metadata import distributions, distribution
from pathlib import Path, PureWindowsPath
from urllib import parse as url_parse

from siliconcompiler.package.cache import PathCache, DataRootResolutionError
from siliconcompiler.utils import get_plugins, default_cache_dir
from siliconcompiler.utils.paths import cwdirsafe
from siliconcompiler.utils.multiprocessing import MPManager

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
        schema (object): The root object (typically a Project) providing context,
            such as environment variables and the working directory.
        source (str): The URI or path specifying the data source.
        reference (str): A version, commit hash, or tag for remote sources.
    """

    def __init__(self, name: str,
                 schema: Optional[Union["Project", "BaseSchema"]],
                 source: str,
                 reference: Optional[str] = None):
        """
        Initializes the Resolver.
        """
        self.__name = name
        self.__schema = schema
        self.__root = None if schema is None else schema._parent(root=True)
        self.__source = source
        self.__reference = reference
        self.__changed = False
        self.__cacheid = None

        if self.__root and hasattr(self.__root, "logger"):
            rootlogger = self.__root.logger
        else:
            rootlogger = MPManager.logger()
        self.__logger = rootlogger.getChild(f"resolver-{self.name}")

    @staticmethod
    def populate_resolvers() -> None:
        """
        Scans for and registers all available resolver plugins.

        This method populates the internal `_RESOLVERS` dictionary with both
        built-in resolvers (file, key, python, http, git, github, scp) and any
        resolvers provided by external plugins. Built-ins are registered first,
        so a plugin claiming the same scheme takes precedence.
        """
        # Imported here because each of these modules imports RemoteResolver from
        # this module.
        from siliconcompiler.package import git, github, https, scp

        settings = MPManager().get_transient_settings()
        if settings.get_category("resolvers"):
            # Already populated
            return

        settings.set("resolvers", "", FileResolver)
        settings.set("resolvers", "file", FileResolver)
        settings.set("resolvers", "key", KeyPathResolver)
        settings.set("resolvers", "python", PythonPathResolver)
        settings.set("resolvers", "dataroot", DatarootResolver)

        builtins = (https.get_resolver, git.get_resolver, github.get_resolver, scp.get_resolver)
        for resolver in (*builtins, *get_plugins("path_resolver")):
            for scheme, res in resolver().items():
                settings.set("resolvers", scheme, res)

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

        Resolver.populate_resolvers()

        url = url_parse.urlparse(source)
        settings = MPManager().get_transient_settings()
        resolver = settings.get("resolvers", url.scheme, None)
        if resolver:
            return resolver

        raise ValueError(f"Source URI '{source}' is not supported")

    @property
    def name(self) -> str:
        """The name of the data package being resolved."""
        return self.__name

    @property
    def display_name(self) -> str:
        """A user-friendly display name for the resolver."""
        if self.__schema:
            keypath = self.__schema._keypath
            if keypath:
                return f"{self.name} [{','.join(keypath)}]"
        return self.name

    @property
    def is_retryable(self) -> bool:
        """
        True if a failed resolution is worth retrying.

        Failures are then counted in the shared cache, delayed with a growing
        backoff, and abandoned once the budget runs out. Only worth doing where an
        attempt is expensive, so remote sources enable it (see
        :class:`RemoteResolver`) while local ones leave it off: they fail
        instantly and identically every time, so a retry cannot help.
        """
        return False

    @property
    def is_indirect(self) -> bool:
        """
        True if this resolver is an indirection rather than a location of its own.

        ``dataroot://name`` and ``key://keypath`` do not name data; they name
        something *within a schema* that in turn names data, and they hand the
        real work to that resolver. Two consequences follow, both applied by
        :meth:`get_path`:

        * An indirection is not cached. The cache is keyed by :attr:`cache_id`, a
          hash of the source URI and reference, which identifies a path only for a
          source that means the same thing everywhere -- an absolute ``file://``
          path, a ``python://`` module, a remote URL at a fixed reference. A
          dataroot name or a keypath means something different in every project or
          design, so caching one would let two schemas collide and hand each other
          the wrong path. Resolving an indirection is cheap, and where it points
          at an expensive source that resolver still caches.
        * An indirection does not announce where data was found, because the
          resolver it delegates to already reported the same location.
        """
        return False

    @property
    def root(self) -> Optional[Union["Project", "BaseSchema"]]:
        """The root object (e.g., Project) providing context."""
        return self.__root

    @property
    def schema(self) -> Optional["BaseSchema"]:
        """The schema object (e.g., Project) providing context."""
        return self.__schema

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

    @property
    def cache(self) -> PathCache:
        """
        :class:`~siliconcompiler.package.cache.PathCache`: The store of paths that
        data sources have resolved to, shared by everything in this process.
        """
        return MPManager.get_path_cache()

    def __abandoned_message(self, cache: PathCache) -> str:
        """Builds the error text used when a data source is given up on."""
        source = self.source
        if self.reference:
            source = f"{source} ({self.reference})"
        return (f"Unable to resolve '{self.display_name}' from {source} after "
                f"{cache.attempts(self.cache_id)} attempt(s), giving up. "
                f"Last error: {cache.failure(self.cache_id)}")

    def get_path(self) -> str:
        """
        Resolves the data source and returns its local path.

        This method first checks the cache of already resolved paths. If the
        source is not cached, it calls `resolve()` and caches the result.

        Each call makes at most one attempt at resolving the source. For sources
        where an attempt is expensive (see :attr:`is_retryable`), failures are
        counted in the shared :class:`~siliconcompiler.package.cache.PathCache`,
        so the repeated lookups a run performs consume a bounded budget rather
        than re-fetching indefinitely. Once the budget is spent, later calls fail
        immediately without touching the network.

        Returns:
            str: The absolute path to the resolved data on the local filesystem.

        Raises:
            FileNotFoundError: If the resolved path does not exist.
            DataRootResolutionError: If the source has already failed to resolve
                :attr:`PathCache.max_attempts` times.
        """
        cache = self.cache

        if not self.is_indirect:
            cache_path: Optional[str] = cache.get(self.cache_id)
            if cache_path:
                return cache_path

        if self.is_retryable:
            if cache.is_exhausted(self.cache_id):
                raise DataRootResolutionError(self.__abandoned_message(cache))

            # Back off before re-attempting a source that has already failed.
            # Delays live in the cache so resolvers stay a single attempt each
            # and no data source type has to implement its own retry policy.
            cache.wait_before_retry(self.cache_id)

        try:
            path = self.resolve()
            if not os.path.exists(path):
                raise FileNotFoundError(f"Unable to locate '{self.display_name}' at {path}")
        except Exception as e:
            # Deliberately narrower than BaseException: a KeyboardInterrupt or
            # SystemExit says nothing about whether the source is reachable, so
            # it must not consume the budget or poison the cache.
            if self.is_retryable:
                if cache.record_failure(self.cache_id, e) >= cache.max_attempts:
                    self.logger.error(self.__abandoned_message(cache))
            raise

        if self.is_retryable:
            cache.clear_failure(self.cache_id)

        if self.is_indirect:
            # An indirection owns no location: the resolver it delegated to has
            # already reported where the data is, and its schema-relative source
            # string is not a safe cache key. See :attr:`is_indirect`.
            return str(path)

        if self.changed:
            self.logger.info(f'Saved {self.display_name} data to {path}')
        else:
            self.logger.info(f'Found {self.display_name} data at {path}')

        cache.set(self.cache_id, path)
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

    @property
    def is_retryable(self) -> bool:
        """
        True. Fetching a remote source is expensive, so give up on one that keeps
        failing instead of letting every caller re-download it.
        """
        return True

    def __init__(self, name: str,
                 schema: Optional[Union["Project", "BaseSchema"]],
                 source: str,
                 reference: Optional[str] = None):
        if reference is None:
            raise ValueError(f'A reference (e.g., version, commit) is required for {name}')

        super().__init__(name, schema, source, reference)

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
        """
        Gets the download lock for this resolver's data source.

        The lock is keyed by :attr:`cache_id`, so resolvers for unrelated sources
        never contend. Note this is not the same granularity as
        :attr:`lock_file`, which is derived from :attr:`cache_name` and so also
        varies with :attr:`name`: two resolvers naming one source differently
        share this lock but take different lock files, because they also download
        to different :attr:`cache_path` directories.
        """
        return self.cache.thread_lock(self.cache_id)

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
            # Only release a lock this context actually took. threading.Lock has
            # no notion of an owner, so releasing on the strength of locked()
            # would let a waiter that timed out free the holder's lock and admit
            # a third thread into the download.
            if lock_acquired:
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
            except BaseException:
                # Exception occurred, so need to cleanup
                try:
                    # Make writable first, in case cache was partially made read-only
                    try:
                        self._make_writable(self.cache_path)
                    except OSError as e:
                        self.logger.warning(f"Could not make cache writable before cleanup: {e}")
                    shutil.rmtree(self.cache_path)
                except BaseException as cleane:
                    self.logger.error(f"Exception occurred during cleanup: {cleane} "
                                      f"({cleane.__class__.__name__})")
                raise

            # Make all cached files read-only to prevent accidental modifications
            try:
                self._make_readonly(self.cache_path)
            except OSError as e:
                self.logger.warning(f"Could not make cache read-only: {e}")

            self.set_changed()
            return self.cache_path

    def _make_readonly(self, path: Union[str, Path]) -> None:
        """
        Recursively makes all files and directories in the given path read-only.

        This prevents accidental modification of cached remote data by removing write
        permissions while preserving executable bits and read access. Note: git does
        not track full file permissions (only the executable bit), so this operation
        will not create a dirty warning in git repositories.

        Any directory named ``.git`` is skipped so git's internal state (including
        ``.git/lfs/tmp`` and per-submodule ``.git/modules/<name>``) stays writable —
        otherwise routine git operations like diff/status fail on LFS-tracked repos
        because the clean filter cannot buffer through ``.git/lfs/tmp``.

        Args:
            path: The path to make read-only (file or directory).
        """
        path = Path(path)
        # Skip symlinks to avoid following them outside the cache
        if path.is_symlink():
            return
        # Preserve writability of git's internal state directories
        if path.is_dir() and path.name == ".git":
            return
        if path.is_file():
            # Remove write permissions, preserve everything else (especially execute bit)
            current_mode = os.stat(path).st_mode
            new_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            os.chmod(path, new_mode)
        elif path.is_dir():
            # Process all contents recursively
            for item in path.iterdir():
                self._make_readonly(item)
            # Remove write permissions from the directory itself
            current_mode = os.stat(path).st_mode
            new_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            os.chmod(path, new_mode)

    def _make_writable(self, path: Union[str, Path]) -> None:
        """
        Recursively makes all files and directories in the given path writable.

        This is used before deletion to ensure that read-only cached files can be
        properly removed when necessary (e.g., for corrupted cache cleanup).

        Args:
            path: The path to make writable (file or directory).
        """
        path = Path(path)
        # Skip symlinks to avoid following them outside the cache
        if path.is_symlink():
            return
        if path.is_file():
            # Add owner write permission, preserve everything else
            current_mode = os.stat(path).st_mode
            new_mode = current_mode | stat.S_IWUSR
            os.chmod(path, new_mode)
        elif path.is_dir():
            # Process all contents recursively
            for item in path.iterdir():
                self._make_writable(item)
            # Add owner write permission to the directory itself
            current_mode = os.stat(path).st_mode
            new_mode = current_mode | stat.S_IWUSR
            os.chmod(path, new_mode)

    def _get_auth_token(self, prefix: List[str]) -> str:
        """
        Retrieves an authentication token from environment variables.

        Args:
            prefix (List[str]): A list of prefixes to search for in environment variable names.
                For example, if prefix is ['GITHUB'], it will look for 'GITHUB_<PACKAGE_NAME>_TOKEN'
                and 'GITHUB_TOKEN'.

        Returns:
            str: The found token.

        Raises:
            ValueError: If no token can be found in the environment.
        """
        token_name = self.name.upper()
        # Sanitize package name for environment variable compatibility
        for char in ('#', '$', '&', '-', '=', '!', '/', '.'):
            token_name = token_name.replace(char, '')

        search_env = []
        for prf in prefix:
            search_env.append(f"{prf.upper()}_{token_name}_TOKEN")
            search_env.append(f"{prf.upper()}_TOKEN")

        for env in search_env:
            token = os.environ.get(env)
            if token:
                return token

        raise ValueError('Unable to determine authorization token. Please set one of the '
                         f'following environment variables: {", ".join(search_env)}')


class FileResolver(Resolver):
    """
    A resolver for local file system paths.

    It handles both absolute paths and paths relative to the project's CWD.
    It normalizes the source string to a `file://` URI.
    """

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        if source.startswith("file://"):
            source = source[7:]
        if source[0] != "$" and not os.path.isabs(source):
            source = os.path.join(cwdirsafe(schema._parent(root=True)), source)

        super().__init__(name, schema, f"file://{source}", None)

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

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        super().__init__(name, schema, source, None)

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

        dist_obj = distribution(dist_name)
        if not dist_obj:
            return False

        direct_url_content = dist_obj.read_text('direct_url.json')
        if direct_url_content:
            direct_url = json.loads(direct_url_content)
            return direct_url.get('dir_info', {}).get('editable', False)

        dist_loc = dist_obj.locate_file('')
        site_paths = site.getsitepackages()
        user_site_path = site.getusersitepackages()
        if user_site_path:
            site_paths.append(user_site_path)
        if not dist_loc or not site_paths:
            return False

        dist_loc = PureWindowsPath(dist_loc).as_posix()
        return dist_loc not in [PureWindowsPath(site_path).as_posix() for site_path in site_paths]

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

    @property
    def is_indirect(self) -> bool:
        """True. A keypath names something inside a schema, not a location."""
        return True

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        super().__init__(name, schema, source, None)

    def resolve(self) -> str:
        """
        Resolves the path by looking up the keypath in the project schema.

        Returns:
            str: The file path found in the schema.

        Raises:
            RuntimeError: If the resolver does not have a root project object defined.
        """
        if not self.root:
            raise RuntimeError(f"A root schema has not been defined for '{self.display_name}'")

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


class DatarootResolver(Resolver):
    """
    A resolver for finding file paths stored with other dataroots.
    """

    @property
    def is_indirect(self) -> bool:
        """
        True. A dataroot name is only meaningful within the schema that defines
        it, and the dataroot it points at is resolved by its own resolver.
        """
        return True

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        super().__init__(name, schema, source, None)
        # Track visited dataroots passed from parent resolver for cycle detection
        self._parent_visited: Optional[set] = None

    def resolve(self) -> str:
        """
        Resolves a dataroot by looking up its configured path and resolving it.

        This resolver looks up a dataroot by name in the dataroot registry, retrieves
        its configured path (which may be a file://, python://, or another dataroot://),
        and resolves that path using the appropriate resolver. This allows dataroots
        to reference other dataroots, forming resolution chains.

        Returns:
            str: The resolved absolute path for the dataroot.

        Raises:
            RuntimeError: If the resolver does not have a root project object defined,
                if the dataroot is not defined in the registry, or if a circular
                dataroot reference is detected during resolution.
        """
        source_schema = self.schema
        if not source_schema:
            raise RuntimeError(f"A schema context is required for '{self.display_name}'")

        datarootstore = self.schema._parent()
        if not datarootstore:
            raise RuntimeError(f"A root schema has not been defined for '{self.display_name}'")

        find_root = self.urlpath
        if not datarootstore.valid('dataroot', self.urlpath):
            raise RuntimeError(
                f"Dataroot '{self.urlpath}' is not defined for '{self.display_name}'")

        # Use visited set from parent, or start new one if this is top-level
        visited = self._parent_visited if self._parent_visited is not None else set()

        # Check for circular dataroot references
        if find_root in visited:
            raise RuntimeError(
                f"Circular dataroot reference detected: '{find_root}' is part of a reference cycle")

        # Mark this dataroot as visited
        visited_copy = visited.copy()
        visited_copy.add(find_root)

        path: str = datarootstore.get("dataroot", find_root, "path")
        tag: Optional[str] = datarootstore.get("dataroot", find_root, "tag")

        resolver = Resolver.find_resolver(path)
        resolver_instance = resolver(self.name, self.schema, path, tag)

        # If the next resolver is also a DatarootResolver, pass the visited set to it
        if isinstance(resolver_instance, DatarootResolver):
            resolver_instance._parent_visited = visited_copy

        base_path = resolver_instance.get_path()
        # Strip leading '/' from urlparse.path to avoid os.path.join treating it as absolute
        subpath = self.urlparse.path.lstrip('/')
        return os.path.join(base_path, subpath) if subpath else base_path
