import contextlib
import functools
import importlib
import json
import logging
import os
import re
import time
import threading

import os.path

from fasteners import InterProcessLock
from importlib.metadata import distributions, distribution
from pathlib import Path
from urllib import parse as url_parse

from siliconcompiler.utils import get_plugins


def path(chip, package):
    import warnings
    warnings.warn("The 'path' method has been deprecated",
                  DeprecationWarning)
    return chip.get("package", field="schema").get_resolver(package).get_path()


def register_python_data_source(chip,
                                package_name,
                                python_module,
                                alternative_path,
                                alternative_ref=None,
                                python_module_path_append=None):
    '''
    Helper function to register a python module as data source with an alternative in case
    the module is not installed in an editable state
    '''
    import warnings
    warnings.warn("The 'register_python_data_source' method was renamed "
                  "PythonPathResolver.register_source",
                  DeprecationWarning)

    PythonPathResolver.register_source(
        chip, package_name, python_module, alternative_path,
        alternative_ref=alternative_ref,
        python_module_path_append=python_module_path_append)


class Resolver:
    _RESOLVERS_LOCK = threading.Lock()
    _RESOLVERS = {}

    def __init__(self, name, root, source, reference=None):
        self.__name = name
        self.__root = root
        self.__source = source
        self.__reference = reference
        self.__changed = False
        self.__cache = {}

        if self.__root and hasattr(self.__root, "logger"):
            self.__logger = self.__root.logger.getChild(f"resolver-{self.name}")
        else:
            self.__logger = logging.getLogger(f"resolver-{self.name}")

    @staticmethod
    def populate_resolvers():
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
    def find_resolver(source):
        if os.path.isabs(source):
            return FileResolver

        if not Resolver._RESOLVERS:
            Resolver.populate_resolvers()

        url = url_parse.urlparse(source)
        with Resolver._RESOLVERS_LOCK:
            if url.scheme in Resolver._RESOLVERS:
                return Resolver._RESOLVERS[url.scheme]

        raise ValueError(f"{source} is not supported")

    @property
    def name(self) -> str:
        return self.__name

    @property
    def root(self):
        return self.__root

    @property
    def logger(self) -> logging.Logger:
        return self.__logger

    @property
    def source(self) -> str:
        return self.__source

    @property
    def reference(self) -> str:
        return self.__reference

    @property
    def urlparse(self) -> url_parse.ParseResult:
        return url_parse.urlparse(self.__resolve_env(self.source))

    @property
    def urlscheme(self) -> str:
        return self.urlparse.scheme

    @property
    def urlpath(self) -> str:
        return self.urlparse.netloc

    @property
    def changed(self):
        change = self.__changed
        self.__changed = False
        return change

    def set_changed(self):
        self.__changed = True

    def set_cache(self, cache):
        self.__cache = cache

    def resolve(self):
        raise NotImplementedError("child class must implement this")

    def get_path(self):
        if self.name in self.__cache:
            return self.__cache[self.name]

        path = self.resolve()
        if not os.path.exists(path):
            raise FileNotFoundError(f"Unable to locate {self.name} at {path}")

        if self.changed and self.name not in self.__cache:
            self.logger.info(f'Saved {self.name} data to {path}')
        else:
            self.logger.info(f'Found {self.name} data at {path}')
        self.__cache[self.name] = path
        return self.__cache[self.name]

    def __resolve_env(self, path):
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
    _CACHE_LOCKS = {}
    _CACHE_LOCK = threading.Lock()

    def __init__(self, name, root, source, reference=None):
        if reference is None:
            raise ValueError(f'Reference is required for cached data: {name}')

        super().__init__(name, root, source, reference)

        # Wait a maximum of 10 minutes for other processes to finish
        self.__max_lock_wait = 60 * 10

    @property
    def timeout(self):
        return self.__max_lock_wait

    def set_timeout(self, value):
        self.__max_lock_wait = value

    @staticmethod
    def determine_cache_dir(root) -> Path:
        default_path = os.path.join(Path.home(), '.sc', 'cache')
        if not root:
            return Path(default_path)

        if root.valid('option', 'cachedir'):
            path = root.get('option', 'cachedir')
            if path:
                path = root.find_files('option', 'cachedir', missing_ok=True)
                if not path:
                    path = os.path.join(getattr(root, "cwd", os.getcwd()),
                                        root.get('option', 'cachedir'))
        if not path:
            path = default_path

        return Path(path)

    @property
    def cache_dir(self) -> Path:
        return RemoteResolver.determine_cache_dir(self.root)

    @property
    def cache_name(self) -> str:
        return f"{self.name}-{self.reference}"

    @property
    def cache_path(self) -> Path:
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        return self.cache_dir / self.cache_name

    @property
    def lock_file(self) -> Path:
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        return self.cache_dir / f"{self.cache_name}.lock"

    @property
    def sc_lock_file(self) -> Path:
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        return self.cache_dir / f"{self.cache_name}.sc_lock"

    def thread_lock(self):
        with RemoteResolver._CACHE_LOCK:
            if self.name not in RemoteResolver._CACHE_LOCKS:
                RemoteResolver._CACHE_LOCKS[self.name] = threading.Lock()
            return RemoteResolver._CACHE_LOCKS[self.name]

    @contextlib.contextmanager
    def lock(self):
        lock = self.thread_lock()
        lock_acquired = False
        try:
            if lock.acquire_lock(timeout=self.timeout):
                data_path_lock = InterProcessLock(self.lock_file)
                sc_data_path_lock = None
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
            if lock.locked():
                lock.release()
            if lock_acquired:
                if data_path_lock.acquired:
                    data_path_lock.release()
                if sc_data_path_lock:
                    sc_data_path_lock.unlink(missing_ok=True)

        if not lock_acquired:
            raise RuntimeError(f'Failed to access {self.cache_path}. '
                               f'{self.lock_file} is still locked, if this is a mistake, '
                               'please delete it.')

    def resolve_remote(self):
        raise NotImplementedError("child class must implement this")

    def check_cache(self):
        raise NotImplementedError("child class must implement this")

    def resolve(self) -> Path:
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except OSError:
                return self.cache_path

        if not os.access(self.cache_dir, os.W_OK):
            return self.cache_path

        with self.lock():
            if self.check_cache():
                return self.cache_path

            self.resolve_remote()
            self.set_changed()
            return self.cache_path


###############
class FileResolver(Resolver):
    def __init__(self, name, root, source, reference=None):
        if source.startswith("file://"):
            source = source[7:]
        if not os.path.isabs(source):
            source = os.path.join(getattr(root, "cwd", os.getcwd()), source)

        super().__init__(name, root, f"file://{source}", None)

    @property
    def urlpath(self):
        parse = self.urlparse
        if parse.netloc:
            return parse.netloc
        else:
            return parse.path

    def resolve(self):
        return os.path.abspath(self.urlpath)


class PythonPathResolver(Resolver):
    def __init__(self, name, root, source, reference=None):
        super().__init__(name, root, source, None)

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_python_module_mapping():
        mapping = {}

        for dist in distributions():
            dist_name = None
            if hasattr(dist, 'name'):
                dist_name = dist.name
            else:
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
                for module in dist.read_text('top_level.txt').split():
                    mapping.setdefault(module, []).append(dist_name)

        return mapping

    @staticmethod
    def is_python_module_editable(module_name):
        dist_map = PythonPathResolver.get_python_module_mapping()
        dist = dist_map[module_name][0]

        is_editable = False
        for f in distribution(dist).files:
            if f.name == 'direct_url.json':
                info = None
                with open(f.locate(), 'r') as f:
                    info = json.load(f)

                if "dir_info" in info:
                    is_editable = info["dir_info"].get("editable", False)

        return is_editable

    @staticmethod
    def register_source(root,
                        package_name,
                        python_module,
                        alternative_path,
                        alternative_ref=None,
                        python_module_path_append=None):
        '''
        Helper function to register a python module as data source with an alternative in case
        the module is not installed in an editable state
        '''
        # check if installed in an editable state
        if PythonPathResolver.is_python_module_editable(python_module):
            if python_module_path_append:
                path = PythonPathResolver(
                    python_module, root, f"python://{python_module}").resolve()
                path = os.path.abspath(os.path.join(path, python_module_path_append))
            else:
                path = f"python://{python_module}"
            ref = None
        else:
            path = alternative_path
            ref = alternative_ref

        root.register_source(name=package_name,
                             path=path,
                             ref=ref)

    def resolve(self):
        module = importlib.import_module(self.urlpath)
        python_path = os.path.dirname(module.__file__)
        return os.path.abspath(python_path)


class KeyPathResolver(Resolver):
    def __init__(self, name, root, source, reference=None):
        super().__init__(name, root, source, None)

    def resolve(self):
        if not self.root:
            raise RuntimeError(f"Root schema has not be defined for {self.name}")

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
