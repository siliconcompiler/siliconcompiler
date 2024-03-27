import os
import requests
import tarfile
from git import Repo, GitCommandError
from urllib.parse import urlparse
import importlib
import shutil
import re
from siliconcompiler import SiliconCompilerError
from siliconcompiler.utils import default_cache_dir
import json
from importlib.metadata import distributions, distribution
import functools
import fasteners

from github import Github
import github.Auth


def path(chip, package):
    """
    Compute data source data path
    Additionally cache data source data if possible
    Parameters:
        package (str): Name of the data source
        quiet (boolean): Suppress package data found messages
    Returns:
        path: Location of data source on the local system
    """

    if package not in chip._packages:
        quiet = False
        chip._packages.add(package)
    else:
        quiet = True

    # Initially try retrieving data source from schema
    data = {}
    data['path'] = chip.get('package', 'source', package, 'path')
    data['ref'] = chip.get('package', 'source', package, 'ref')
    if not data['path']:
        chip.error(f'Could not find package source for {package} in schema.')
        chip.error('You can use register_package_source() to add it.', fatal=True)

    data['path'] = chip._resolve_env_vars(data['path'])

    url = urlparse(data['path'])

    # check network drive for package data source
    if data['path'].startswith('file://') or os.path.exists(data['path']):
        path = os.path.abspath(data['path'].replace('file://', ''))
        if not quiet:
            chip.logger.info(f'Found {package} data at {path}')
        return path
    elif data['path'].startswith('python://'):
        path = path_from_python(chip, url.netloc)
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
        chip.error(f'Could not find data path in package {package}: {data["path"]}', fatal=True)
    data_path = os.path.join(cache_path, project_id)
    data_path_lock = os.path.join(cache_path, f'{project_id}.lock')

    data_lock = fasteners.InterProcessLock(data_path_lock)

    _aquire_data_lock(data_path, data_lock)

    # check cached package data source
    if os.path.exists(data_path):
        if not quiet:
            chip.logger.info(f'Found cached {package} data at {data_path}')
        if url.scheme in ['git', 'git+https', 'ssh', 'git+ssh']:
            try:
                repo = Repo(data_path)
                if not quiet and (repo.untracked_files or repo.index.diff("HEAD")):
                    chip.logger.warning('The repo of the cached data is dirty.')
                return data_path
            except GitCommandError:
                chip.logger.warning('Deleting corrupted cache data.')
                shutil.rmtree(path)
        else:
            data_lock.release()
            return data_path

    # download package data source
    if url.scheme in ['git', 'git+https', 'ssh', 'git+ssh']:
        clone_synchronized(chip, package, data, data_path)
    elif url.scheme == 'https':
        extract_from_url(chip, package, data, data_path)

    data_lock.release()

    if os.path.exists(data_path):
        chip.logger.info(f'Saved {package} data to {data_path}')
        return data_path
    raise SiliconCompilerError(f'Extracting {package} data to {data_path} failed')


def _aquire_data_lock(data_path, data_lock):
    # Wait a maximum of 10 minutes for other processes to finish
    if not data_lock.acquire(timeout=60 * 10):
        raise SiliconCompilerError(f'Failed to access {data_path}. '
                                   f'{data_lock.path} is still locked, if this is a mistake, '
                                   'please delete it.')


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
                            'or use ssh for authentification.')
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
    if not data_url.endswith('.tar.gz') and not data_url.endswith('.tgz'):
        data_url = f"{data['path']}{data['ref']}.tar.gz"
    chip.logger.info(f'Downloading {package} data from {data_url}')
    response = requests.get(data_url, stream=True, headers=headers)
    if not response.ok:
        chip.error('Failed to download package data source.', fatal=True)
    file = tarfile.open(fileobj=response.raw, mode='r|gz')
    file.extractall(path=data_path)

    # Git inserts one folder at the highest level of the tar file
    # This moves all files one level up
    shutil.copytree(os.path.join(data_path, os.listdir(data_path)[0]),
                    data_path, dirs_exist_ok=True, symlinks=True)


def path_from_python(chip, python_package, append_path=None):
    try:
        module = importlib.import_module(python_package)
    except:  # noqa E722
        chip.error(f'Failed to import {python_package}.', fatal=True)

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

    chip.register_package_source(name=package_name,
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

    chip.register_package_source(
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
