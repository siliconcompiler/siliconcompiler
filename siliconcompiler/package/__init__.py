import os
from urllib.parse import urlparse
import importlib
import re
from siliconcompiler import SiliconCompilerError
from siliconcompiler.utils import default_cache_dir
import json
from importlib.metadata import distributions, distribution
import functools
import time
from pathlib import Path

from siliconcompiler.utils import get_plugins, get_env_vars
from siliconcompiler.schema.parametervalue import PathNodeValue


def get_cache_path(chip):
    cache_path = chip.get('option', 'cachedir')
    if cache_path:
        cache_path = chip.find_files('option', 'cachedir', missing_ok=True)
        if not cache_path:
            cache_path = os.path.join(chip.cwd, chip.get('option', 'cachedir'))
    if not cache_path:
        cache_path = default_cache_dir()

    return cache_path


def get_download_cache_path(chip, package, ref):
    cache_path = get_cache_path(chip)
    if not os.path.exists(cache_path):
        os.makedirs(cache_path, exist_ok=True)

    if ref is None:
        raise SiliconCompilerError(f'Reference is required for cached data: {package}', chip=chip)

    return \
        os.path.join(cache_path, f'{package}-{ref}'), \
        os.path.join(cache_path, f'{package}-{ref}.lock')


def _file_path_resolver(chip, package, path, ref, url, fetch):
    return os.path.abspath(path.replace('file://', ''))


def _python_path_resolver(chip, package, path, ref, url, fetch):
    return path_from_python(chip, url.netloc)


def _key_path_resolver(chip, package, path, ref, url, fetch):
    key = url.netloc.split(',')
    if chip.get(*key, field='pernode').is_never():
        paths = chip.find_files(*key)
    else:
        paths = chip.find_files(*key, step=chip.get('arg', 'step'), index=chip.get('arg', 'index'))

    if isinstance(paths, list):
        return paths[0]
    return paths


def _get_path_resolver(path):
    url = urlparse(path)

    for resolver in get_plugins("path_resolver"):
        func = resolver(url)
        if func:
            return func, url

    if url.scheme == "key":
        return _key_path_resolver, url

    if url.scheme == "file":
        return _file_path_resolver, url

    if url.scheme == "python":
        return _python_path_resolver, url

    raise ValueError(f"{path} is not supported")


def _path(chip, package, fetch):
    # Initially try retrieving data source from schema
    data = {}
    data['path'] = chip.get('package', 'source', package, 'path')
    data['ref'] = chip.get('package', 'source', package, 'ref')
    if not data['path']:
        if package.startswith("key://"):
            data['path'] = package
        else:
            raise SiliconCompilerError(
                f'Could not find package source for {package} in schema. '
                'You can use register_source() to add it.', chip=chip)

    env_vars = get_env_vars(chip, None, None)
    data['path'] = PathNodeValue.resolve_env_vars(data['path'], envvars=env_vars)

    if os.path.exists(data['path']):
        # Path is already a path
        return os.path.abspath(data['path'])

    path_resolver, url = _get_path_resolver(data['path'])

    return path_resolver(chip, package, data['path'], data['ref'], url, fetch)


def path(chip, package, fetch=True):
    """
    Compute data source data path
    Additionally cache data source data if possible
    Parameters:
        package (str): Name of the data source
        fetch (bool): Flag to indicate that the path should be fetched
    Returns:
        path: Location of data source on the local system
    """

    if package not in chip._packages:
        changed = False
        data_path = _path(chip, package, fetch)

        if isinstance(data_path, tuple) and len(data_path) == 2:
            data_path, changed = data_path

        if package.startswith("key://"):
            return data_path

        if os.path.exists(data_path):
            if package not in chip._packages and changed:
                chip.logger.info(f'Saved {package} data to {data_path}')
            else:
                chip.logger.info(f'Found {package} data at {data_path}')

            chip._packages[package] = data_path
        else:
            raise SiliconCompilerError(f'Unable to locate {package} data in {data_path}',
                                       chip=chip)

    return chip._packages[package]


def __get_filebased_lock(data_lock):
    base, _ = os.path.splitext(os.fsdecode(data_lock.path))
    return Path(f'{base}.sc_lock')


def aquire_data_lock(data_path, data_lock):
    # Wait a maximum of 10 minutes for other processes to finish
    max_seconds = 10 * 60
    try:
        if data_lock.acquire(timeout=max_seconds):
            return
    except RuntimeError:
        # Fall back to file based locking method
        lock_file = __get_filebased_lock(data_lock)
        while (lock_file.exists()):
            if max_seconds == 0:
                raise SiliconCompilerError(f'Failed to access {data_path}.'
                                           f'Lock {lock_file} still exists.')
            time.sleep(1)
            max_seconds -= 1

        lock_file.touch()

        return

    raise SiliconCompilerError(f'Failed to access {data_path}. '
                               f'{data_lock.path} is still locked, if this is a mistake, '
                               'please delete it.')


def release_data_lock(data_lock):
    # Check if file based locking method was used
    lock_file = __get_filebased_lock(data_lock)
    if lock_file.exists():
        lock_file.unlink(missing_ok=True)
        return

    data_lock.release()


def path_from_python(chip, python_package, append_path=None):
    try:
        module = importlib.import_module(python_package)
    except:  # noqa E722
        raise SiliconCompilerError(f'Failed to import {python_package}.', chip=chip)

    python_path = os.path.dirname(module.__file__)
    if append_path:
        if isinstance(append_path, str):
            append_path = [append_path]
        python_path = os.path.join(python_path, *append_path)

    python_path = os.path.abspath(python_path)

    return python_path


def is_python_module_editable(module_name):
    dist_map = __get_python_module_mapping()
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
    # check if installed in an editable state
    if is_python_module_editable(python_module):
        if python_module_path_append:
            path = path_from_python(chip, python_module, append_path=python_module_path_append)
        else:
            path = f"python://{python_module}"
        ref = None
    else:
        path = alternative_path
        ref = alternative_ref

    chip.register_source(name=package_name,
                         path=path,
                         ref=ref)


@functools.lru_cache(maxsize=1)
def __get_python_module_mapping():
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


def register_private_github_data_source(chip,
                                        package_name,
                                        repository,
                                        release,
                                        artifact):
    chip.register_source(
        package_name,
        path=f"github+private://{repository}/{release}/{artifact}",
        ref=release)
