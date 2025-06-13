import shutil

import os.path

from git import Repo, GitCommandError
from siliconcompiler.package import RemoteResolver


def get_resolver():
    return {
        "git": GitResolver,
        "git+https": GitResolver,
        "git+ssh": GitResolver,
        "ssh": GitResolver
    }


class GitResolver(RemoteResolver):
    def __init__(self, name, root, source, reference=None):
        super().__init__(name, root, source, reference)

    def check_cache(self):
        if os.path.exists(self.cache_path):
            try:
                repo = Repo(self.cache_path)
                if repo.untracked_files or repo.index.diff("HEAD"):
                    self.logger.warning('The repo of the cached data is dirty.')
                return True
            except GitCommandError:
                self.logger.warning('Deleting corrupted cache data.')
                shutil.rmtree(self.cache_path)
                return False
        return False

    def __get_token_env(self):
        token_name = self.name.upper()
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
                return token
        return None

    @property
    def git_path(self):
        if self.urlscheme == "git+ssh":
            return f"ssh://{self.urlpath}{self.urlparse.path}"
        if self.urlscheme == "ssh":
            return self.source
        url = self.urlparse
        if not url.username and self.__get_token_env():
            url = url._replace(netloc=f'{self.__get_token_env()}@{url.hostname}')
        url = url._replace(scheme='https')
        return url.geturl()

    def resolve_remote(self):
        try:
            path = self.git_path
            self.logger.info(f'Cloning {self.name} data from {path}')
            repo = Repo.clone_from(path, self.cache_path, recurse_submodules=True)
            self.logger.info(f'Checking out {self.reference}')
            repo.git.checkout(self.reference)
            for submodule in repo.submodules:
                submodule.update(recursive=True, init=True, force=True)
        except GitCommandError as e:
            if 'Permission denied' in repr(e):
                if self.urlscheme in ('ssh', 'git+ssh'):
                    raise RuntimeError('Failed to authenticate. Please setup your git ssh.')
                elif self.urlscheme in ('git', 'git+https'):
                    raise RuntimeError('Failed to authenticate. Please use a token or ssh.')
            else:
                raise e
