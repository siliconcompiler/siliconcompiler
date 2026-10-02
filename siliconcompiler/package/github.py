"""
This module provides the GitHub resolvers for SiliconCompiler packages.

It defines `GithubArchiveResolver`, which handles plain ``http(s)://`` URLs on
GitHub's own hosts, and `GithubResolver`, which downloads release assets named
by a ``github://`` URI from public or private repositories.
"""
import shutil
import subprocess

from typing import Dict, List, Type, Optional, Tuple, TYPE_CHECKING

from github import Github, Auth
from github.GithubException import UnknownObjectException
from urllib.parse import ParseResult, urlparse

from siliconcompiler.package.https import HTTPResolver

if TYPE_CHECKING:
    from siliconcompiler.project import Project

#: Archive suffixes stripped from a GitHub archive's filename to recover the
#: release reference its top-level directory is named after.
#:
#: The fallback for a name matching none of these gives up at the first '.', which
#: truncates any release carrying a dotted version -- 'v1.0.2.tar.zst' would look
#: for 'repo-1' rather than 'repo-1.0.2'. No entry is a suffix of another, so the
#: first match is the whole extension.
#:
#: One format is deliberately absent: a plain, uncompressed '.tar' is not among the
#: formats :func:`siliconcompiler.package.https._archive_formats` can read, so an
#: archive named that way never reaches the flattening this table serves.
_ARCHIVE_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst",
                     ".tgz", ".tbz2", ".txz", ".tzst", ".zip")


def get_resolver() -> Dict[str, Type["GithubResolver"]]:
    """
    Returns a dictionary mapping GitHub URI schemes to the GithubResolver class.

    This function is used by the resolver system to discover and register this
    resolver for handling `github` and `github+private` protocols. Plain
    ``http(s)://`` URLs on GitHub's hosts need no entry: `HTTPResolver` hands
    them to `GithubArchiveResolver`.

    Returns:
        dict: A dictionary mapping scheme names to the GithubResolver class.
    """
    return {
        "github": GithubResolver,
        "github+private": GithubResolver
    }


class GithubArchiveResolver(HTTPResolver):
    """
    A resolver for archives downloaded from GitHub's own hosts over HTTP(S).

    `HTTPResolver` hands it every ``http(s)://`` URL on a GitHub host, so a plain
    ``https://github.com/<owner>/<repo>/archive/...`` dataroot gets what GitHub
    needs without being written as ``github://``: the source archive is
    unwrapped from its ``<repo>-<ref>`` directory, a release asset is asked for
    as a file rather than as its JSON description, and -- on a host GitHub owns
    -- GitHub's tokens are sent.
    """

    @classmethod
    def claims(cls, url: ParseResult) -> bool:
        """
        Whether ``url`` is on a GitHub host, GitHub Enterprise included.

        Matched by label (:meth:`_host_forge`), so ``github.mycorp.com`` is
        claimed: it packs its archives as github.com does. That is not evidence
        that GitHub owns the host, which :meth:`_token_prefixes` checks for
        itself.
        """
        return cls._host_forge(url.hostname) == "github"

    def _get_headers(self) -> Dict[str, str]:
        headers = super()._get_headers()
        # A release asset by its API URL answers with JSON unless asked for the file.
        headers['Accept'] = 'application/octet-stream'
        return headers

    def _token_prefixes(self, data_url: str) -> List[str]:
        prefixes = super()._token_prefixes(data_url)
        # Ownership, not the label match that claimed the URL: GitHub's variables
        # are set ambiently -- GITHUB_TOKEN in every Actions job -- so GitHub
        # Enterprise, or github.attacker.example, must not be handed them.
        if self._saas_forge(urlparse(data_url).hostname) == "github":
            prefixes = ["GITHUB", "GH", "GIT", *prefixes]
        return prefixes

    def _archive_root(self, data_url: str) -> Optional[str]:
        """
        The directory a GitHub source archive wraps the repository in.

        GitHub names it ``<repo>-<ref>``, with any leading ``v`` dropped from the
        ref: ``github.com/<owner>/<repo>/archive/refs/tags/v1.0.tar.gz`` unpacks
        into ``<repo>-1.0``. Both halves are read from the URL, the repository
        from the path segment after the owner and the ref from the filename.

        Args:
            data_url (str): The archive's URL.

        Returns:
            str or None: The directory's name, or None for a path too short to
            name a repository.
        """
        path = urlparse(data_url).path.split('/')
        if len(path) < 3:
            return None
        repo = path[2]

        ref = path[-1]
        for suffix in _ARCHIVE_SUFFIXES:
            if ref.endswith(suffix):
                ref = ref[0:-len(suffix)]
                break
        else:
            # An unrecognized name keeps the long-standing guess, which gives up at
            # its first '.' and so truncates a dotted release.
            ref = ref.split('.')[0]

        if ref.startswith('v'):
            ref = ref[1:]

        return f"{repo}-{ref}"


class GithubResolver(GithubArchiveResolver):
    """
    A resolver for fetching release assets from GitHub repositories.

    This class extends `GithubArchiveResolver` to interact with the GitHub API
    for locating and downloading release assets. It supports both public
    and private repositories. A source archive (`<release>.tar.gz` or
    `<release>.zip`) is unwrapped as any GitHub source archive is; a release asset
    is left as its author packed it.

    The expected source URI format is:
    `github://<owner>/<repository>/<release_tag>/<asset_name>`

    For private repositories, the scheme should be `github+private://` and
    a GitHub token must be provided via environment variables.
    """

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        """
        Initializes the GithubResolver.
        """
        super().__init__(name, schema, source, reference)

        self.__url = None

        if len(self.gh_path) != 4:
            raise ValueError(
                f"'{self.source}' is not in the proper form: "
                "github://<owner>/<repository>/<version>/<artifact>")

    @property
    def gh_path(self) -> Tuple[str, ...]:
        """
        Parses the source URL into its constituent GitHub parts.

        Returns:
            tuple: A tuple containing (owner, repository, release_tag, asset_name).
        """
        return self.urlpath, *self.urlparse.path.split("/")[1:]

    @property
    def download_url(self) -> str:
        """
        Determines the direct download URL for the GitHub release asset.

        This method first attempts to find the asset in a public repository.
        If that fails (e.g., with an `UnknownObjectException`), it then tries
        to find it in a private repository, which requires authentication.
        The `github+private` scheme forces an authenticated private lookup directly.

        Returns:
            str: The direct URL to download the asset.
        """
        url_parts = self.gh_path
        repository = "/".join(url_parts[0:2])
        release = url_parts[2]
        artifact = url_parts[3]

        if self.is_private:
            return self.__get_release_url(repository, release, artifact, private=True)

        try:
            # First, try as a public repository
            return self.__get_release_url(repository, release, artifact, private=False)
        except UnknownObjectException:
            # If public access fails, try as a private repository
            self.logger.info("Could not find public release, trying private.")
            return self.__get_release_url(repository, release, artifact, private=True)

    def _get_headers(self):
        headers = super()._get_headers()

        try:
            headers['Authorization'] = f'token {self.__get_gh_token()}'
        except ValueError:
            pass

        return headers

    def _archive_root(self, data_url: str) -> Optional[str]:
        _, _, release, artifact = self.gh_path
        if artifact in (f"{release}.tar.gz", f"{release}.zip"):
            return super()._archive_root(data_url)
        return None

    def __get_release_url(self, repository: str, release: str, artifact: str, private: bool) -> str:
        """
        Uses the GitHub API to find the download URL for a specific release asset.

        Also handles special cases for downloading source code archives (`.zip`
        or `.tar.gz`).

        Args:
            repository (str): The repository name in 'owner/repo' format.
            release (str): The release tag (e.g., 'v1.0.0').
            artifact (str): The filename of the asset to download.
            private (bool): If True, use an authenticated API client.

        Returns:
            str: The direct download URL for the asset.

        Raises:
            ValueError: If the specified release or asset cannot be found.
        """
        if self.__url is not None:
            return self.__url

        # Handle standard source code archive names
        if artifact == f"{release}.zip":
            return f"https://github.com/{repository}/archive/refs/tags/{release}.zip"
        if artifact == f"{release}.tar.gz":
            return f"https://github.com/{repository}/archive/refs/tags/{release}.tar.gz"

        # Use the GitHub API for other assets
        repo = self.__gh(private).get_repo(repository)

        if not release:
            release = repo.get_latest_release().tag_name
            self.logger.info(f"No release specified, using latest: {release}")

        repo_release = repo.get_release(release)
        if repo_release:
            for asset in repo_release.assets:
                if asset.name == artifact:
                    self.__url = asset.url
                    return asset.url

        raise ValueError(f'Unable to find release asset: {repository}/{release}/{artifact}')

    def __get_gh_token(self) -> str:
        try:
            return super()._get_auth_token(["GITHUB", "GH", "GIT"])
        except ValueError as e:
            # Try calling gh
            gh = shutil.which("gh")
            if gh:
                try:
                    run = subprocess.run([gh, "auth", "token"], capture_output=True, timeout=5)
                except subprocess.TimeoutExpired:
                    raise e
                if run.returncode == 0:
                    token = run.stdout.decode().strip()
                    if not token or '\n' in token or '\r' in token:
                        raise e
                    return token
            raise e

    def __gh(self, private: bool) -> Github:
        """
        Initializes the PyGithub client.

        Args:
            private (bool): If True, initializes the client with an authentication
                token. Otherwise, initializes an unauthenticated client.

        Returns:
            Github: An initialized PyGithub client instance.
        """
        if private:
            return Github(auth=Auth.Token(self.__get_gh_token()))
        else:
            return Github()
