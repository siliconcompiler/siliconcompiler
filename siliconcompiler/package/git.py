import shutil

import os.path

from git import Repo, GitCommandError
from fasteners import InterProcessLock

from siliconcompiler.package import get_download_cache_path
from siliconcompiler.package import aquire_data_lock, release_data_lock


def get_resolver(url):
    if url.scheme in ("git", "git+https", "git+ssh", "ssh"):
        return git_resolver
    return None


def git_resolver(chip, package, path, ref, url, fetch):
    data_path, data_path_lock = get_download_cache_path(chip, package, ref)

    if not fetch:
        return data_path, False

    # Acquire lock
    data_lock = InterProcessLock(data_path_lock)
    aquire_data_lock(data_path, data_lock)

    if os.path.exists(data_path):
        try:
            repo = Repo(data_path)
            if repo.untracked_files or repo.index.diff("HEAD"):
                chip.logger.warning('The repo of the cached data is dirty.')
            release_data_lock(data_lock)
            return data_path, False
        except GitCommandError:
            chip.logger.warning('Deleting corrupted cache data.')
            shutil.rmtree(data_path)

    clone_synchronized(chip, package, path, ref, url, data_path)

    release_data_lock(data_lock)

    return data_path, True


def clone_synchronized(chip, package, path, ref, url, data_path):
    try:
        clone_from_git(chip, package, path, ref, url, data_path)
    except GitCommandError as e:
        if 'Permission denied' in repr(e):
            if url.scheme in ['ssh', 'git+ssh']:
                chip.logger.error('Failed to authenticate. Please setup your git ssh.')
            elif url.scheme in ['git', 'git+https']:
                chip.logger.error('Failed to authenticate. Please use a token or ssh.')
        else:
            chip.logger.error(str(e))


def clone_from_git(chip, package, path, ref, url, data_path):
    if url.scheme in ['git', 'git+https'] and url.username:
        chip.logger.warning('Your token is in the data source path and will be stored in the '
                            'schema. If you do not want this set the env variable GIT_TOKEN '
                            'or use ssh for authentication.')
    if url.scheme in ['git+ssh']:
        chip.logger.info(f'Cloning {package} data from {url.netloc}:{url.path[1:]}')
        # Git requires the format git@github.com:org/repo instead of git@github.com/org/repo
        repo = Repo.clone_from(f'{url.netloc}/{url.path[1:]}',
                               data_path,
                               recurse_submodules=True)
    elif url.scheme in ['ssh']:
        chip.logger.info(f'Cloning {package} data from {path}')
        repo = Repo.clone_from(path,
                               data_path,
                               recurse_submodules=True)
    else:
        if os.environ.get('GIT_TOKEN') and not url.username:
            url = url._replace(netloc=f'{os.environ.get("GIT_TOKEN")}@{url.hostname}')
        url = url._replace(scheme='https')
        chip.logger.info(f'Cloning {package} data from {url.geturl()}')
        repo = Repo.clone_from(url.geturl(), data_path, recurse_submodules=True)
    chip.logger.info(f'Checking out {ref}')
    repo.git.checkout(ref)
    for submodule in repo.submodules:
        submodule.update(recursive=True, init=True, force=True)
