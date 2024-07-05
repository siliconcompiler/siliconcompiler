import os
import requests
import tarfile
import zipfile
from git import Repo, GitCommandError
from urllib.parse import urlparse
import importlib
import shutil
import re
from siliconcompiler import SiliconCompilerError
from siliconcompiler.utils import default_cache_dir, _resolve_env_vars
import json
from importlib.metadata import distributions, distribution
import functools
import fasteners
import time
from pathlib import Path
from io import BytesIO

from github import Github
import github.Auth


def get_cache_path(chip):
    cache_path = chip.get('option', 'cachedir')
    if cache_path:
        cache_path = chip.find_files('option', 'cachedir', missing_ok=True)
        if not cache_path:
            cache_path = os.path.join(chip.cwd, chip.get('option', 'cachedir'))
    if not cache_path:
        cache_path = default_cache_dir()

    return cache_path


def _path(chip, package, download_handler):
    if package in chip._packages:
        return chip._packages[package]

    # Initially try retrieving data source from schema
    data = {}
    data['path'] = chip.get('package', 'source', package, 'path')
    data['ref'] = chip.get('package', 'source', package, 'ref')
    if not data['path']:
        raise SiliconCompilerError(
            f'Could not find package source for {package} in schema. '
            'You can use register_source() to add it.', chip=chip)

    data['path'] = _resolve_env_vars(chip, data['path'])

    url = urlparse(data['path'])

    # check network drive for package data source
    if data['path'].startswith('file://') or os.path.exists(data['path']):
        path = os.path.abspath(data['path'].replace('file://', ''))
        chip.logger.info(f'Found {package} data at {path}')
        chip._packages[package] = path
        return path
    elif data['path'].startswith('python://'):
        path = path_from_python(chip, url.netloc)
        chip.logger.info(f'Found {package} data at {path}')
        chip._packages[package] = path
        return path

    # location of the python package
    cache_path = get_cache_path(chip)
    if not os.path.exists(cache_path):
        os.makedirs(cache_path, exist_ok=True)
    project_id = f'{package}-{data.get("ref")}'
    if url.scheme not in ['git', 'git+https', 'https', 'git+ssh', 'ssh'] or not project_id:
        raise SiliconCompilerError(
            f'Could not find data path in package {package}: {data["path"]}',
            chip=chip)

    data_path = os.path.join(cache_path, project_id)

    if download_handler:
        download_handler(chip,
                         package,
                         data,
                         url,
                         data_path,
                         os.path.join(cache_path, f'{project_id}.lock'))

    if os.path.exists(data_path):
        if package not in chip._packages:
            chip.logger.info(f'Saved {package} data to {data_path}')
            chip._packages[package] = data_path
        return data_path

    raise SiliconCompilerError(f'Extracting {package} data to {data_path} failed')


def path(chip, package):
    """
    Compute data source data path
    Additionally cache data source data if possible
    Parameters:
        package (str): Name of the data source
    Returns:
        path: Location of data source on the local system
    """

    return _path(chip, package, __download_data)


def __download_data(chip, package, data, url, data_path, data_path_lock):
    data_lock = fasteners.InterProcessLock(data_path_lock)

    _aquire_data_lock(data_path, data_lock)

    # check cached package data source
    if os.path.exists(data_path):
        chip.logger.info(f'Found cached {package} data at {data_path}')
        if url.scheme in ['git', 'git+https', 'ssh', 'git+ssh']:
            try:
                repo = Repo(data_path)
                if repo.untracked_files or repo.index.diff("HEAD"):
                    chip.logger.warning('The repo of the cached data is dirty.')
                _release_data_lock(data_lock)
                chip._packages[package] = data_path
                return
            except GitCommandError:
                chip.logger.warning('Deleting corrupted cache data.')
                shutil.rmtree(path)
        else:
            _release_data_lock(data_lock)
            chip._packages[package] = data_path
            return

    # download package data source
    if url.scheme in ['git', 'git+https', 'ssh', 'git+ssh']:
        clone_synchronized(chip, package, data, data_path)
    elif url.scheme == 'https':
        extract_from_url(chip, package, data, data_path)

    _release_data_lock(data_lock)


def __get_filebased_lock(data_lock):
    base, _ = os.path.splitext(os.fsdecode(data_lock.path))
    return Path(f'{base}.sc_lock')


def _aquire_data_lock(data_path, data_lock):
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


def _release_data_lock(data_lock):
    # Check if file based locking method was used
    lock_file = __get_filebased_lock(data_lock)
    if lock_file.exists():
        lock_file.unlink(missing_ok=True)
        return

    data_lock.release()


def clone_synchronized(chip, package, data, data_path):
    url = urlparse(data['path'])
    try:
        clone_from_git(chip, package, data, data_path)
    except GitCommandError as e:
        if 'Permission denied' in repr(e):
            if url.scheme in ['ssh', 'git+ssh']:
                chip.logger.error('Failed to authenticate. Please setup your git ssh.')
            elif url.scheme in ['git', 'git+https']:
                chip.logger.error('Failed to authenticate. Please use a token or ssh.')
        else:
            raise e


def clone_from_git(chip, package, data, repo_path):
    url = urlparse(data['path'])
    if url.scheme in ['git', 'git+https'] and url.username:
        chip.logger.warning('Your token is in the data source path and will be stored in the '
                            'schema. If you do not want this set the env variable GIT_TOKEN '
                            'or use ssh for authentication.')
    if url.scheme in ['git+ssh', 'ssh']:
        chip.logger.info(f'Cloning {package} data from {url.netloc}:{url.path[1:]}')
        # Git requires the format git@github.com:org/repo instead of git@github.com/org/repo
        repo = Repo.clone_from(f'{url.netloc}:{url.path[1:]}',
                               repo_path,
                               recurse_submodules=True)
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
    if "github" in data_url:
        headers['Accept'] = 'application/octet-stream'
    data_url = data['path']
    if data_url.endswith('/'):
        data_url = f"{data_url}{data['ref']}.tar.gz"
    chip.logger.info(f'Downloading {package} data from {data_url}')
    response = requests.get(data_url, stream=True, headers=headers)
    if not response.ok:
        raise SiliconCompilerError(f'Failed to download {package} data source.', chip=chip)

    fileobj = BytesIO(response.content)
    try:
        with tarfile.open(fileobj=fileobj, mode='r|gz') as tar_ref:
            tar_ref.extractall(path=data_path)
    except tarfile.ReadError:
        fileobj.seek(0)
        # Try as zip
        with zipfile.ZipFile(fileobj) as zip_ref:
            zip_ref.extractall(path=data_path)

    if 'github' in url.netloc and len(os.listdir(data_path)) == 1:
        # Github inserts one folder at the highest level of the tar file
        # this compensates for this behavior
        gh_url = urlparse(data_url)

        repo = gh_url.path.split('/')[2]

        ref = gh_url.path.split('/')[-1]
        if repo.endswith('.git'):
            ref = data['ref']
        elif ref.endswith('.tar.gz'):
            ref = ref[0:-7]
        elif ref.endswith('.tgz'):
            ref = ref[0:-4]
        else:
            ref = ref.split('.')[0]

        if ref.startswith('v'):
            ref = ref[1:]

        github_folder = f"{repo}-{ref}"

        if github_folder in os.listdir(data_path):
            # This moves all files one level up
            git_path = os.path.join(data_path, github_folder)
            for data_file in os.listdir(git_path):
                shutil.move(os.path.join(git_path, data_file), data_path)
            os.removedirs(git_path)


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


def register_private_github_data_source(chip,
                                        package_name,
                                        repository,
                                        release,
                                        artifact):
    gh = Github(auth=github.Auth.Token(__get_github_auth_token(package_name)))
    repo = gh.get_repo(repository)

    if not release:
        release = repo.get_latest_release().tag_name

    url = None
    for repo_release in repo.get_releases():
        if repo_release.tag_name == release:
            for asset in repo_release.assets:
                if asset.name == artifact:
                    url = asset.url

    if not url:
        raise ValueError(f'Unable to find release asset: {repository}/{release}/{artifact}')

    chip.register_source(
        package_name,
        path=url,
        ref=release)


def __get_github_auth_token(package_name):
    token_name = package_name.upper()
    for tok in ('#', '$', '&', '-', '=', '!', '/'):
        token_name = token_name.replace(tok, '')

    search_env = (
        f'GITHUB_{token_name}_TOKEN',
        'GITHUB_TOKEN',
        'GIT_TOKEN'
    )

    token = None
    for env in search_env:
        token = os.environ.get(env, None)

        if token:
            break

    if not token:
        raise ValueError('Unable to determine authorization token for GitHub, '
                         f'please set one of the following environmental variables: {search_env}')

    return token


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
