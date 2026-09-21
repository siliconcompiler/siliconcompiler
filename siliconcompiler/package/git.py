"""
This module provides a Git-based resolver for SiliconCompiler packages.

It defines the `GitResolver` class, which is responsible for cloning remote
Git repositories into a local cache, checking out specific references (like
branches, tags, or commit hashes), and managing the cached repository's state.
"""
import shutil
import os.path
import sys

from typing import Dict, Type, Optional, TYPE_CHECKING

from git import Repo, GitCommandError
from urllib import parse as url_parse

from siliconcompiler.package import RemoteResolver

if TYPE_CHECKING:
    from siliconcompiler.project import Project


class GitAuthenticationError(RuntimeError):
    """
    Raised when a Git remote refuses, or never receives, a usable credential.

    Subclasses :class:`RuntimeError`, which is what this resolver has always
    raised for an authentication failure, so existing handlers keep working. The
    distinct type is what lets :meth:`GitResolver.is_permanent_failure` tell a
    settled credential problem from a transient network one.
    """


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

    @staticmethod
    def _host_forge(hostname: Optional[str]) -> Optional[str]:
        """
        Identifies which forge a hostname belongs to.

        Matches whole dot-separated labels, so a self-hosted instance
        (``gitlab.example.com``, ``github.mycorp.com``) is recognised while an
        unrelated host that merely contains the name (``mygithub.internal``) is
        not.

        Args:
            hostname (str or None): The host from the source URL.

        Returns:
            str or None: The forge key, or None if the host is unrecognised.
        """
        if not hostname:
            return None
        labels = hostname.lower().split('.')
        for forge in ("github", "gitlab", "bitbucket"):
            if forge in labels:
                return forge
        return None

    @classmethod
    def _token_username(cls, hostname: Optional[str]) -> Optional[str]:
        """
        Returns the basic-auth username ``hostname`` expects with a token.

        Git gets a single unprompted attempt at a credential: if the host refuses
        what the URL carries there is no second chance, only a password prompt
        that a machine with no terminal can answer. A bare token in the username
        field with an empty password is accepted by GitHub for classic personal
        access tokens but not for App installation tokens, and by GitLab for
        neither, so the username is chosen here rather than left for the server
        to infer.

        Args:
            hostname (str or None): The host from the source URL.

        Returns:
            str or None: The username to pair the token with, or None if the host
            is unrecognised and the token has to go in the username field itself.
        """
        return {
            "github": "x-access-token",
            "gitlab": "oauth2",
            "bitbucket": "x-token-auth",
        }.get(cls._host_forge(hostname))

    def _get_token(self, hostname: Optional[str]) -> Optional[str]:
        """
        Finds an authentication token for ``hostname`` in the environment.

        The host's own prefixes are searched before the generic ``GIT`` one, so
        ``GITHUB_TOKEN`` and ``GITLAB_TOKEN`` are honoured for their own hosts
        while ``GIT_TOKEN`` keeps working everywhere.

        Args:
            hostname (str or None): The host from the source URL.

        Returns:
            str or None: The token, or None if the environment holds none.
        """
        srvs = {
            "github": ["GITHUB", "GH"],
            "gitlab": ["GITLAB", "GL"],
            "bitbucket": ["BITBUCKET"],
        }.get(self._host_forge(hostname), [])
        try:
            return self._get_auth_token(srvs + ["GIT"])
        except ValueError:
            return None

    @staticmethod
    def _git_env() -> Dict[str, str]:
        """
        Environment overrides applied to the git commands this resolver runs.

        With no credential to hand, git opens ``/dev/tty`` to ask for one. Where
        there is no terminal that fails as ``No such device or address``, an
        errno standing in for what is really an authentication error. Disabling
        the prompt where it could never have been answered turns the class of
        failure back into a clean one. An interactive session is left alone, so a
        developer without a token is still asked for one.

        Returns:
            dict: Environment variables to set, empty when running interactively.
        """
        try:
            interactive = sys.stdin is not None and sys.stdin.isatty()
        except (AttributeError, ValueError):
            # stdin may be closed or replaced by something without a descriptor
            interactive = False
        if interactive:
            return {}
        return {'GIT_TERMINAL_PROMPT': '0'}

    @property
    def git_path(self) -> str:
        """
        Constructs the final Git URL for cloning.

        This method handles different URL schemes and automatically injects
        an authentication token into HTTPS URLs if a token is found in the
        environment.

        The token is sent as the basic-auth *password*, under the username the
        host expects (see ``_token_username``). Putting it in the username field
        with no password, as this once did, leaves git one refusable attempt and
        then a password prompt: GitHub accepts that shape for a classic personal
        access token but not for an App installation token, and GitLab accepts it
        for neither. A username already present in the URL wins, which is how a
        host this does not know about can still be reached.

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
        token = self._get_token(url.hostname)

        # A password already in the URL is the user's own credential; leave it be.
        # An empty one (``user:@host``) counts as supplied, hence 'is None'.
        if token and url.netloc and url.password is None:
            # Host and port, with any existing userinfo removed. url.hostname is
            # not usable here: it drops the port and unwraps IPv6 brackets.
            host = url.netloc.rpartition('@')[2]
            user = url.username or self._token_username(url.hostname)
            if user:
                userinfo = f'{url_parse.quote(user, safe="")}:' \
                           f'{url_parse.quote(token, safe="")}'
            else:
                # Unrecognised host: send the token where it has always gone, but
                # spell the empty password out. Identical on the wire, and it stops
                # git falling through to a prompt nothing can answer.
                userinfo = f'{url_parse.quote(token, safe="")}:'
            url = url._replace(netloc=f'{userinfo}@{host}')
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
        env = self._git_env()
        if env:
            repo.git.update_environment(**env)
        try:
            repo.git.lfs("pull")
        except GitCommandError as e:
            msg = f"{e}".lower()
            if "lfs" in msg and ("is not a git command" in msg or "not found" in msg):
                raise RuntimeError(
                    "Repository uses Git LFS but 'git-lfs' is not installed. "
                    "Install git-lfs or pass '?lfs=false' in the source URL to skip.")
            raise

    def is_permanent_failure(self, error: BaseException) -> bool:
        """
        Widens the base rule with Git's authentication failures.

        A credential that a host has refused, or that was never supplied, earns
        the same answer on every attempt. Retrying it spends the whole budget --
        and the backoff between each try -- to arrive where the first attempt
        already was.

        Args:
            error (BaseException): The error a resolution attempt raised.

        Returns:
            bool: True if the source should be abandoned without further attempts.
        """
        if isinstance(error, GitAuthenticationError):
            return True
        return super().is_permanent_failure(error)

    def resolve_remote(self) -> None:
        """
        Fetches the remote repository and checks out the specified reference.

        This method performs the `git clone` operation, followed by `git checkout`
        on the specified branch, tag, or commit. It also initializes all submodules
        and fetches Git LFS objects when applicable.

        Raises:
            GitAuthenticationError: If the remote refused, or never received, a
                usable credential.
            RuntimeError: If LFS is required but git-lfs is not installed.
            GitCommandError: For other Git-related errors.
        """
        env = self._git_env()
        try:
            path = self.git_path
            self.logger.info(f'Cloning {self.display_name} data from {path}')
            repo = Repo.clone_from(path, self.cache_path,
                                   recurse_submodules=self.include_submodules,
                                   env=env or None)
            if env:
                # clone_from's env covers only the clone itself; the checkout,
                # submodule and LFS steps below run through this repo's git.
                repo.git.update_environment(**env)

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
            # What git says for a credential that was refused, missing, or
            # unobtainable. 'could not read Username'/'Password' are what it
            # reports when it falls through to a prompt it cannot show, which on
            # a runner surfaces as an errno rather than an authentication error.
            auth_errors = ('Permission denied',
                           'could not read Username',
                           'could not read Password',
                           'Authentication failed',
                           'Invalid username or password',
                           'Invalid username or token')
            if any(marker in error_msg for marker in auth_errors):
                if self.urlscheme in ('ssh', 'git+ssh'):
                    raise GitAuthenticationError(
                        'Failed to authenticate with Git. Please ensure your SSH '
                        'keys are set up correctly.')
                else:  # 'git', 'git+https'
                    raise GitAuthenticationError(
                        'Failed to authenticate with Git. Please provide a token '
                        'via GITHUB_TOKEN, GITLAB_TOKEN or GIT_TOKEN, or use an SSH URL.')
            else:
                # Re-raise other Git errors
                raise
