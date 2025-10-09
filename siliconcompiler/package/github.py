"""
This module provides a GitHub-based resolver for SiliconCompiler packages.

It defines the `GithubResolver` class, which is responsible for downloading
release assets from public or private GitHub repositories.
"""
import os

from typing import Dict, Type, Optional, Tuple, TYPE_CHECKING

from github import Github, Auth
from github.GithubException import UnknownObjectException

from siliconcompiler.package.https import HTTPResolver

if TYPE_CHECKING:
    from siliconcompiler.project import Project


def get_resolver() -> Dict[str, Type["GithubResolver"]]:
    """
    Returns a dictionary mapping GitHub URI schemes to the GithubResolver class.

    This function is used by the resolver system to discover and register this
    resolver for handling `github` and `github+private` protocols.

    Returns:
        dict: A dictionary mapping scheme names to the GithubResolver class.
    """
    return {
        "github": GithubResolver,
        "github+private": GithubResolver
    }


class GithubResolver(HTTPResolver):
    """
    A resolver for fetching release assets from GitHub repositories.

    This class extends the `HTTPResolver` to interact with the GitHub API
    for locating and downloading release assets. It supports both public
    and private repositories.

    The expected source URI format is:
    `github://<owner>/<repository>/<release_tag>/<asset_name>`

    For private repositories, the scheme should be `github+private://` and
    a GitHub token must be provided via environment variables.
    """

    def __init__(self, name: str, root: "Project", source: str, reference: Optional[str] = None):
        """
        Initializes the GithubResolver.
        """
        super().__init__(name, root, source, reference)

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

        if self.urlscheme == "github+private":
            return self.__get_release_url(repository, release, artifact, private=True)

        try:
            # First, try as a public repository
            return self.__get_release_url(repository, release, artifact, private=False)
        except UnknownObjectException:
            # If public access fails, try as a private repository
            self.logger.info("Could not find public release, trying private.")
            return self.__get_release_url(repository, release, artifact, private=True)

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
                    return asset.url

        raise ValueError(f'Unable to find release asset: {repository}/{release}/{artifact}')

    def __get_gh_auth(self) -> str:
        """
        Searches for a GitHub authentication token in predefined environment variables.

        The search order is:
        1. GITHUB_<PACKAGE_NAME>_TOKEN
        2. GITHUB_TOKEN
        3. GIT_TOKEN

        Returns:
            str: The found token.

        Raises:
            ValueError: If no token can be found in the environment.
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

        token = None
        for env in search_env:
            token = os.environ.get(env)
            if token:
                break

        if not token:
            raise ValueError('Unable to determine authorization token for GitHub. '
                             'Please set one of the following environment variables: '
                             f'{", ".join(search_env)}')

        return token

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
            return Github(auth=Auth.Token(self.__get_gh_auth()))
        else:
            return Github()
