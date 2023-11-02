import os
import requests
import tarfile
from pathlib import Path
import importlib
from git import Repo, GitCommandError
from urllib.parse import urlparse
import shutil
from time import sleep


def path(chip, package):
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
            'commitid': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866',
            'name': 'your-dependency'
            or
            'path': e.g. 'git://github.com/xyz/xyz/'
            'commitid': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866',
            'name': 'your-dependency'
            or
            'path': e.g. 'git+ssh://github.com/xyz/xyz/'
            'commitid': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866',
            'name': 'your-dependency'
            or
            'path': e.g. 'ssh://github.com/xyz/xyz/'
            'commitid': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866',
            'name': 'your-dependency'
            or
            'path': e.g. 'https://github.com/xyz/xyz/archive/',
            'commitid': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866',
            'name': 'your-dependency'
            or
            'path': e.g. 'https://zeroasic.com/xyz.tar.gz',
            'name': e.g. 'your-dependency-version-1'
    Returns:
    string: Location of dependency data
    """

    # Initially try retrieving dependency from schema
    dependency = {}
    dependency['path'] = chip.get('dependency', package, 'path')
    dependency['commitid'] = chip.get('dependency', package, 'commitid')
    dependency['name'] = chip.get('dependency', package, 'name')
    if not dependency['path']:
        # If not in the schema retrieve dependency from the python package and store in schema
        dependency = importlib.import_module(package).dependency
        for k, v in dependency.items():
            chip.set('dependency', package, k, v)

    if not dependency.get('path'):
        chip.logger.error('A valid path needs to be specified')
    url = urlparse(dependency['path'])

    # check network drive for dependency data
    if (url.scheme == 'file' or not url.scheme and not url.netloc) and os.path.exists(url.path):
        chip.logger.debug(f'Found network dependency data at {url.path}')
        return url.path

    # location of the python package
    cache_path = os.path.join(Path.home(), '.sc', 'cache')
    if not os.path.exists(cache_path):
        os.makedirs(cache_path, exist_ok=True)
    if dependency.get('name') and dependency.get('commitid'):
        project_id = dependency['name'] + '-' + dependency['commitid']
    else:
        project_id = dependency.get('name')
    if url.scheme not in ['git', 'git+https', 'https', 'git+ssh', 'ssh'] or not project_id:
        chip.error(f'Could not find dependency data in package {package.__name__}')
    data_path = os.path.join(cache_path, project_id)

    # Wait a maximum of 10 minutes for other git processes to finish
    lock_file = Path(data_path+'.lock')
    max_seconds = 600
    while (lock_file.exists()):
        if max_seconds == 0:
            chip.logger.error(f'Failed to access {data_path}.')
            chip.logger.error(f'Lock {lock_file} still exists.')
            exit(1)
        sleep(1)
        max_seconds -= 1

    # check cached dependency data
    if os.path.exists(data_path):
        chip.logger.debug(f'Found cached dependency data at {data_path}')
        return data_path

    # download dependency data
    if url.scheme in ['git', 'git+https', 'ssh', 'git+ssh']:
        try:
            lock_file.touch()
            clone_from_git(chip, dependency, data_path)
        except GitCommandError as e:
            lock_file.unlink()
            if 'Permission denied' in repr(e):
                if url.scheme in ['ssh', 'git+ssh']:
                    chip.logger.error('Failed to authenticate. Please setup your git ssh.')
                elif url.scheme in ['git', 'git+https']:
                    chip.logger.error('Failed to authenticate. Please use a token or ssh.')
            else:
                raise e
        finally:
            lock_file.unlink(missing_ok=True)
    elif url.scheme == 'https':
        extract_from_url(chip, dependency, data_path)
    if os.path.exists(data_path):
        chip.logger.info(f'Saved dependency data to {data_path}')
        return data_path
    chip.logger.error(f'Extracting dependency data to {data_path} failed')
    # Exit clean and early as missing dependencies would definitely cause further issues
    exit(1)


def clone_from_git(chip, dependency, repo_path):
    url = urlparse(dependency['path'])
    if url.scheme in ['git', 'git+https'] and url.username:
        chip.logger.warning('Your token is in the dependency path and will be stored in the schema.'
                            " If you don't want this set the env variable GIT_TOKEN "
                            'or use ssh for authentification.')
    if url.scheme in ['git+ssh', 'ssh']:
        chip.logger.info(f'Cloning dependency data from {url.netloc}:{url.path[1:]}')
        # Git requires the format git@github.com:org/repo instead of git@github.com/org/repo
        repo = Repo.clone_from(f'{url.netloc}:{url.path[1:]}', repo_path, no_checkout=True)
    else:
        if os.environ.get('GIT_TOKEN') and not url.username:
            url = url._replace(netloc=f'{os.environ.get("GIT_TOKEN")}@{url.hostname}')
        url = url._replace(scheme='https')
        chip.logger.info(f'Cloning dependency data from {url.geturl()}')
        repo = Repo.clone_from(url.geturl(), repo_path, no_checkout=True)
    chip.logger.info(f'Checking out {dependency["commitid"]}')
    repo.git.checkout(dependency["commitid"])


def extract_from_url(chip, dependency, data_path):
    url = urlparse(dependency['path'])
    dependency_url = dependency.get('path')
    headers = {}
    if os.environ.get('GIT_TOKEN') or url.username:
        headers['Authorization'] = f'token {os.environ.get("GIT_TOKEN") or url.username}'
    if dependency.get('commitid'):
        dependency_url = dependency['path'] + dependency['commitid'] + '.tar.gz'
    chip.logger.info(f'Downloading dependency data from {dependency_url}')
    response = requests.get(dependency_url, stream=True, headers=headers)
    if not response.ok:
        chip.error('Failed to download dependency')
    file = tarfile.open(fileobj=response.raw, mode='r|gz')
    file.extractall(path=data_path)

    # Git inserts one folder at the highest level of the tar file
    # This moves all files one level up
    shutil.copytree(os.path.join(data_path, os.listdir(data_path)[0]),
                    data_path, dirs_exist_ok=True)
