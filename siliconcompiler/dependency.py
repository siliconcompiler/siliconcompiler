import os
import requests
import tarfile
from pathlib import Path
from git import Repo, GitCommandError
from urllib.parse import urlparse
import shutil
from time import sleep
from siliconcompiler import SiliconCompilerError


def path(chip, package, quiet=True):
    """
    Compute dependency data path
    Additionally cache dependency data if possible
    Parameters:
    arg1 (package): Package with dependency source info
        package.dependency (dict):
            Mandatory keys:
            'path': '/path/on/network/drive',
            or
            'path': 'file:///path/on/network/drive',
            or
            'path': e.g. 'git+https://github.com/xyz/xyz/'
            'ref': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866'
            or
            'path': e.g. 'git://github.com/xyz/xyz/'
            'ref': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866'
            or
            'path': e.g. 'git+ssh://github.com/xyz/xyz/'
            'ref': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866'
            or
            'path': e.g. 'ssh://github.com/xyz/xyz/'
            'ref': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866'
            or
            'path': e.g. 'https://github.com/xyz/xyz/archive/',
            'ref': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866'
            or
            'path': e.g. 'https://zeroasic.com/xyz.tar.gz',
            'ref': e.g. 'your-dependency-version-1'
    Returns:
    string: Location of dependency data
    """

    # Initially try retrieving dependency from schema
    dependency = {}
    dependency['path'] = chip.get('dependency', package, 'path')
    dependency['ref'] = chip.get('dependency', package, 'ref')
    if not dependency['path']:
        chip.logger.error(f'Could not find package source for {package} in schema.')
        chip.logger.error('You can use register_package_source() to add it.')

    if not dependency.get('path'):
        chip.logger.error('A valid path needs to be specified')
    url = urlparse(dependency['path'])

    # check network drive for dependency data
    if dependency['path'].startswith('file://') or os.path.exists(dependency['path']):
        path = dependency['path'].replace('file://', '')
        if not quiet:
            chip.logger.info(f'Found {dependency} data at {path}')
        return path

    # location of the python package
    cache_path = os.path.join(Path.home(), '.sc', 'cache')
    if not os.path.exists(cache_path):
        os.makedirs(cache_path, exist_ok=True)
    project_id = f'{package}-{dependency.get("ref")}'
    if url.scheme not in ['git', 'git+https', 'https', 'git+ssh', 'ssh'] or not project_id:
        chip.error(f'Could not find dependency data in package {package}')
    data_path = os.path.join(cache_path, project_id)

    # Wait a maximum of 10 minutes for other git processes to finish
    lock_file = Path(data_path+'.lock')
    wait_on_lock(chip, data_path, lock_file, max_seconds=600)

    # check cached dependency data
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

    # download dependency data
    if url.scheme in ['git', 'git+https', 'ssh', 'git+ssh']:
        clone_synchronized(chip, package, dependency, data_path, lock_file)
    elif url.scheme == 'https':
        extract_from_url(chip, package, dependency, data_path)
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


def clone_synchronized(chip, package, dependency, data_path, lock_file):
    url = urlparse(dependency['path'])
    try:
        lock_file.touch()
        clone_from_git(chip, package, dependency, data_path)
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


def clone_from_git(chip, package, dependency, repo_path):
    url = urlparse(dependency['path'])
    if url.scheme in ['git', 'git+https'] and url.username:
        chip.logger.warning('Your token is in the dependency path and will be stored in the schema.'
                            " If you don't want this set the env variable GIT_TOKEN "
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
    chip.logger.info(f'Checking out {dependency["ref"]}')
    repo.git.checkout(dependency["ref"], recurse_submodules=True)


def extract_from_url(chip, package, dependency, data_path):
    url = urlparse(dependency['path'])
    dependency_url = dependency.get('path')
    headers = {}
    if os.environ.get('GIT_TOKEN') or url.username:
        headers['Authorization'] = f'token {os.environ.get("GIT_TOKEN") or url.username}'
    dependency_url = dependency['path'] + dependency['ref'] + '.tar.gz'
    chip.logger.info(f'Downloading {package} data from {dependency_url}')
    response = requests.get(dependency_url, stream=True, headers=headers)
    if not response.ok:
        chip.logger.warning('Failed to download dependency. Trying without ref.')
        response = requests.get(dependency['path'], stream=True, headers=headers)
        if not response.ok:
            chip.error('Failed to download dependency without ref.')
    file = tarfile.open(fileobj=response.raw, mode='r|gz')
    file.extractall(path=data_path)

    # Git inserts one folder at the highest level of the tar file
    # This moves all files one level up
    shutil.copytree(os.path.join(data_path, os.listdir(data_path)[0]),
                    data_path, dirs_exist_ok=True, symlinks=True)
