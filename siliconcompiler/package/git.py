"""
This module provides a Git-based resolver for SiliconCompiler packages.

It defines the `GitResolver` class, which is responsible for cloning remote
Git repositories into a local cache, checking out specific references (like
branches, tags, or commit hashes), and managing the cached repository's state.
"""
import shutil
import os.path

from typing import Dict, Type, Optional, Union, TYPE_CHECKING

from git import Repo, GitCommandError
from siliconcompiler.package import RemoteResolver

if TYPE_CHECKING:
    from siliconcompiler.project import Project


def get_resolver() -> Dict[str, Type["GitResolver"]]:
    """
    Returns a dictionary mapping Git-related URI schemes to the GitResolver class.

    This function is used by the resolver system to discover and register this
    resolver for handling git, git+https, git+ssh, and ssh protocols.

    Returns:
        dict: A dictionary mapping scheme names to the GitResolver class.
    """
    return {
        "git": GitResolver,
        "git+https": GitResolver,
        "git+ssh": GitResolver,
        "ssh": GitResolver
    }


class GitResolver(RemoteResolver):
    """
    A resolver for fetching data from remote Git repositories.

    This class handles cloning repositories, checking out specific references,
    and managing the local cache. It supports authentication via environment
    tokens (e.g., GITHUB_TOKEN) for HTTPS and assumes SSH keys are configured
    for SSH-based URLs.
    """

    def __init__(self, name: str, root: "Project", source: str, reference: Optional[str] = None):
        """
        Initializes the GitResolver.
        """
        super().__init__(name, root, source, reference)

    def check_cache(self) -> bool:
        """
        Checks if a valid, clean Git repository exists at the cache path.

        This method verifies that the path points to a valid Git repository
        and warns the user if the repository is "dirty" (has untracked files
        or uncommitted changes). If the repository is corrupted, it is removed.

        Returns:
            bool: True if a valid repository exists, False otherwise.
        """
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

    def __get_token_env(self) -> Union[None, str]:
        """
        Searches for a Git authentication token in predefined environment variables.

        The search order is:
        1. GITHUB_<PACKAGE_NAME>_TOKEN (e.g., GITHUB_SKYWATER130_TOKEN)
        2. GITHUB_TOKEN
        3. GIT_TOKEN

        Returns:
            str or None: The found token, or None if no token is set.
        """
        token_name = self.name.upper()
        # Sanitize package name for environment variable compatibility
        for char in ('#', '$', '&', '-', '=', '!', '/'):
            token_name = token_name.replace(char, '')

        search_env = (
            f'GITHUB_{token_name}_TOKEN',
            'GITHUB_TOKEN',
            'GIT_TOKEN'
        )

        for env in search_env:
            token = os.environ.get(env)
            if token:
                return token
        return None

    @property
    def git_path(self) -> str:
        """
        Constructs the final Git URL for cloning.

        This method handles different URL schemes and automatically injects
        an authentication token into HTTPS URLs if a token is found in the
        environment.

        Returns:
            str: The fully-formed URL ready for `git clone`.
        """
        if self.urlscheme == "git+ssh" or self.urlscheme == "ssh":
            # Reconstruct the original SSH URL
            return self.source.replace('git+', '')

        # For HTTPS, inject token if available
        url = self.urlparse
        token = self.__get_token_env()
        if not url.username and token:
            url = url._replace(netloc=f'{token}@{url.hostname}')
        # Ensure the scheme is HTTPS
        url = url._replace(scheme='https')
        return url.geturl()

    def resolve_remote(self) -> None:
        """
        Fetches the remote repository and checks out the specified reference.

        This method performs the `git clone` operation, followed by `git checkout`
        on the specified branch, tag, or commit. It also initializes all submodules.

        Raises:
            RuntimeError: If authentication fails.
            GitCommandError: For other Git-related errors.
        """
        try:
            path = self.git_path
            self.logger.info(f'Cloning {self.name} data from {path}')
            repo = Repo.clone_from(path, self.cache_path, recurse_submodules=True)

            self.logger.info(f'Checking out {self.reference}')
            repo.git.checkout(self.reference)

            self.logger.info('Updating submodules')
            for submodule in repo.submodules:
                submodule.update(recursive=True, init=True, force=True)
        except GitCommandError as e:
            if 'Permission denied' in repr(e) or 'could not read Username' in repr(e):
                if self.urlscheme in ('ssh', 'git+ssh'):
                    raise RuntimeError('Failed to authenticate with Git. Please ensure your SSH '
                                       'keys are set up correctly.')
                else:  # 'git', 'git+https'
                    raise RuntimeError('Failed to authenticate with Git. Please provide a token '
                                       'via GITHUB_TOKEN or use an SSH URL.')
            else:
                # Re-raise other Git errors
                raise e
