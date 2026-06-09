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
from urllib import parse as url_parse

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

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        """
        Initializes the GitResolver.
        """
        super().__init__(name, schema, source, reference)

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
                # Make writable first, in case cache was previously made read-only
                try:
                    self._make_writable(self.cache_path)
                except OSError as e:
                    self.logger.warning(f"Could not make cache writable before deletion: {e}")
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
            url = self.urlparse
            url = url._replace(scheme='ssh', query="", fragment="")
            return url.geturl()

        # For HTTPS, inject token if available
        url = self.urlparse
        token = None
        try:
            srvs = []
            if "github" in url.hostname:
                srvs.append("GITHUB")
                srvs.append("GH")
            srvs.append("GIT")
            token = self._get_auth_token(srvs)
        except ValueError:
            pass
        if not url.username and token:
            url = url._replace(netloc=f'{token}@{url.hostname}')
        # Ensure the scheme is HTTPS
        url = url._replace(scheme='https', query="", fragment="")
        return url.geturl()

    def __get_query_bool(self, key: str, default: bool) -> bool:
        """
        Parses a boolean query-string parameter from the source URL.

        Raises:
            ValueError: If the value is not a recognised boolean string.
        """
        qs = self.urlparse.query
        if not qs:
            return default
        for qs_key, value in url_parse.parse_qsl(qs):
            if qs_key == key:
                if value.lower() in ("true", "t", "1"):
                    return True
                elif value.lower() in ("false", "f", "0"):
                    return False
                else:
                    raise ValueError(f"{value} is not a valid option for {key}")
        return default

    @property
    def include_submodules(self) -> bool:
        """Returns true if submodules should be included"""
        return self.__get_query_bool("submodules", True)

    @property
    def include_lfs(self) -> bool:
        """Returns true if Git LFS objects should be fetched"""
        return self.__get_query_bool("lfs", True)

    @staticmethod
    def _repo_uses_submodules(repo_path: str) -> bool:
        """
        Returns True if the repository at ``repo_path`` declares submodules
        via a ``.gitmodules`` file at its root.
        """
        return os.path.isfile(os.path.join(repo_path, ".gitmodules"))

    @staticmethod
    def _repo_uses_lfs(repo_path: str) -> bool:
        """
        Returns True if the repository at ``repo_path`` declares LFS-tracked
        files via a ``.gitattributes`` entry containing ``filter=lfs``.
        """
        gitattributes = os.path.join(repo_path, ".gitattributes")
        if not os.path.isfile(gitattributes):
            return False
        try:
            with open(gitattributes, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "filter=lfs" in line:
                        return True
        except OSError:
            return False
        return False

    def _pull_lfs(self, repo: "Repo") -> None:
        """
        Runs ``git lfs pull`` on the given repo if it has LFS-tracked files.

        Raises:
            RuntimeError: If the repo uses LFS but ``git-lfs`` is not installed.
        """
        if not self._repo_uses_lfs(repo.working_dir):
            return
        self.logger.info(f'Fetching LFS objects for {repo.working_dir}')
        try:
            repo.git.lfs("pull")
        except GitCommandError as e:
            msg = f"{e}".lower()
            if "lfs" in msg and ("is not a git command" in msg or "not found" in msg):
                raise RuntimeError(
                    "Repository uses Git LFS but 'git-lfs' is not installed. "
                    "Install git-lfs or pass '?lfs=false' in the source URL to skip.")
            raise

    def resolve_remote(self) -> None:
        """
        Fetches the remote repository and checks out the specified reference.

        This method performs the `git clone` operation, followed by `git checkout`
        on the specified branch, tag, or commit. It also initializes all submodules
        and fetches Git LFS objects when applicable.

        Raises:
            RuntimeError: If authentication fails or LFS is required but git-lfs
                is not installed.
            GitCommandError: For other Git-related errors.
        """
        try:
            path = self.git_path
            self.logger.info(f'Cloning {self.display_name} data from {path}')
            repo = Repo.clone_from(path, self.cache_path,
                                   recurse_submodules=self.include_submodules)

            self.logger.info(f'Checking out {self.reference}')
            repo.git.checkout(self.reference)

            has_submodules = (self.include_submodules
                              and self._repo_uses_submodules(repo.working_dir))
            if has_submodules:
                self.logger.info('Updating submodules')
                for submodule in repo.submodules:
                    submodule.update(recursive=True, init=True, force=True)

            if self.include_lfs:
                self._pull_lfs(repo)
                if has_submodules:
                    for submodule in repo.submodules:
                        self._pull_lfs(submodule.module())
        except GitCommandError as e:
            error_msg = str(e)
            if 'Permission denied' in error_msg or 'could not read Username' in error_msg:
                if self.urlscheme in ('ssh', 'git+ssh'):
                    raise RuntimeError('Failed to authenticate with Git. Please ensure your SSH '
                                       'keys are set up correctly.')
                else:  # 'git', 'git+https'
                    raise RuntimeError('Failed to authenticate with Git. Please provide a token '
                                       'via GITHUB_TOKEN or use an SSH URL.')
            else:
                # Re-raise other Git errors
                raise
