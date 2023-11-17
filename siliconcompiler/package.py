import os
import requests
import tarfile
from pathlib import Path
from git import Repo, GitCommandError
from urllib.parse import urlparse
import importlib
import shutil
from time import sleep
from siliconcompiler import SiliconCompilerError
from siliconcompiler.utils import default_cache_dir


def path(chip, package, quiet=True):
    """
    Compute data source data path
    Additionally cache data source data if possible
    Parameters:
        package (str): Name of the data source
        quiet (boolean): Suppress package data found messages
    Returns:
        path: Location of data source on the local system
    """

    # Initially try retrieving data source from schema
    data = {}
    data['path'] = chip.get('package', 'source', package, 'path')
    data['ref'] = chip.get('package', 'source', package, 'ref')
    if not data['path']:
        chip.error(f'Could not find package source for {package} in schema.')
        chip.error('You can use register_package_source() to add it.', fatal=True)

    url = urlparse(data['path'])

    # check network drive for package data source
    if data['path'].startswith('file://') or os.path.exists(data['path']):
        path = os.path.abspath(data['path'].replace('file://', ''))
        if not quiet:
            chip.logger.info(f'Found {package} data at {path}')
        return path
    elif data['path'].startswith('python://'):
        path = path_from_python(chip, data)
        if not quiet:
            chip.logger.info(f'Found {package} data at {path}')
        return path

    # location of the python package
    cache_path = chip.get('option', 'cache')
    if cache_path:
        cache_path = chip.find_files('option', 'cache', missing_ok=True)
        if not cache_path:
            cache_path = os.path.join(chip.cwd, chip.get('option', 'cache'))
    if not cache_path:
        cache_path = default_cache_dir()
    if not os.path.exists(cache_path):
        os.makedirs(cache_path, exist_ok=True)
    project_id = f'{package}-{data.get("ref")}'
    if url.scheme not in ['git', 'git+https', 'https', 'git+ssh', 'ssh'] or not project_id:
        chip.error(f'Could not find data in package {package}')
    data_path = os.path.join(cache_path, project_id)

    # Wait a maximum of 10 minutes for other git processes to finish
    lock_file = Path(data_path+'.lock')
    wait_on_lock(chip, data_path, lock_file, max_seconds=600)

    # check cached package data source
    if os.path.exists(data_path):
        if not quiet:
            chip.logger.info(f'Found cached {package} data at {data_path}')
        if url.scheme in ['git', 'git+https', 'ssh', 'git+ssh']:
            try:
                lock_file.touch()
                repo = Repo(data_path)
                if not quiet and (repo.untracked_files or repo.index.diff("HEAD")):
                    chip.logger.warning('The repo of the cached data is dirty.')
                return data_path
            except GitCommandError:
                chip.logger.warning('Deleting corrupted cache data.')
                shutil.rmtree(path)
            finally:
                lock_file.unlink(missing_ok=True)
        else:
            return data_path

    # download package data source
    if url.scheme in ['git', 'git+https', 'ssh', 'git+ssh']:
        clone_synchronized(chip, package, data, data_path, lock_file)
    elif url.scheme == 'https':
        extract_from_url(chip, package, data, data_path)
    if os.path.exists(data_path):
        chip.logger.info(f'Saved {package} data to {data_path}')
        return data_path
    raise SiliconCompilerError(f'Extracting {package} data to {data_path} failed')


def wait_on_lock(chip, data_path, lock_file, max_seconds):
    while (lock_file.exists()):
        if max_seconds == 0:
            raise SiliconCompilerError(f'Failed to access {data_path}.'
                                       f'Lock {lock_file} still exists.')
        sleep(1)
        max_seconds -= 1


def clone_synchronized(chip, package, data, data_path, lock_file):
    url = urlparse(data['path'])
    try:
        lock_file.touch()
        clone_from_git(chip, package, data, data_path)
    except GitCommandError as e:
        if 'Permission denied' in repr(e):
            if url.scheme in ['ssh', 'git+ssh']:
                chip.logger.error('Failed to authenticate. Please setup your git ssh.')
            elif url.scheme in ['git', 'git+https']:
                chip.logger.error('Failed to authenticate. Please use a token or ssh.')
        else:
            raise e
    finally:
        lock_file.unlink(missing_ok=True)


def clone_from_git(chip, package, data, repo_path):
    url = urlparse(data['path'])
    if url.scheme in ['git', 'git+https'] and url.username:
        chip.logger.warning('Your token is in the data source path and will be stored in the '
                            'schema. If you do not want this set the env variable GIT_TOKEN '
                            'or use ssh for authentification.')
    if url.scheme in ['git+ssh', 'ssh']:
        chip.logger.info(f'Cloning {package} data from {url.netloc}:{url.path[1:]}')
        # Git requires the format git@github.com:org/repo instead of git@github.com/org/repo
        repo = Repo.clone_from(f'{url.netloc}:{url.path[1:]}', repo_path, recurse_submodules=True)
    else:
        if os.environ.get('GIT_TOKEN') and not url.username:
            url = url._replace(netloc=f'{os.environ.get("GIT_TOKEN")}@{url.hostname}')
        url = url._replace(scheme='https')
        chip.logger.info(f'Cloning {package} data from {url.geturl()}')
        repo = Repo.clone_from(url.geturl(), repo_path, recurse_submodules=True)
    chip.logger.info(f'Checking out {data["ref"]}')
    repo.git.checkout(data["ref"])
    for submodule in repo.submodules:
        submodule.update(init=True)


def extract_from_url(chip, package, data, data_path):
    url = urlparse(data['path'])
    data_url = data.get('path')
    headers = {}
    if os.environ.get('GIT_TOKEN') or url.username:
        headers['Authorization'] = f'token {os.environ.get("GIT_TOKEN") or url.username}'
    data_url = data['path'] + data['ref'] + '.tar.gz'
    chip.logger.info(f'Downloading {package} data from {data_url}')
    response = requests.get(data_url, stream=True, headers=headers)
    if not response.ok:
        chip.logger.warning('Failed to download package data source. Trying without ref.')
        response = requests.get(data['path'], stream=True, headers=headers)
        if not response.ok:
            chip.error('Failed to download package data source without ref.')
    file = tarfile.open(fileobj=response.raw, mode='r|gz')
    file.extractall(path=data_path)

    # Git inserts one folder at the highest level of the tar file
    # This moves all files one level up
    shutil.copytree(os.path.join(data_path, os.listdir(data_path)[0]),
                    data_path, dirs_exist_ok=True, symlinks=True)


def path_from_python(chip, data):
    url = urlparse(data['path'])

    try:
        module = importlib.import_module(url.netloc)
    except:  # noqa E722
        chip.error(f'Failed to import {url.netloc}.', fatal=True)

    return os.path.dirname(module.__file__)
