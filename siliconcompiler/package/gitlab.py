"""
This module provides a GitLab resolver for SiliconCompiler packages.

It defines the `GitlabResolver` class, which downloads a release asset, or a
project's source archive at a release, from gitlab.com or a self-hosted
instance.
"""
import requests

from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

from urllib.parse import quote, unquote, urlparse

from siliconcompiler.package.cache import DataSourceUnavailableError
from siliconcompiler.package.https import HTTPResolver, _TERMINAL_STATUSES

if TYPE_CHECKING:
    from siliconcompiler.project import Project

#: The source archive formats the GitLab API serves that can be unpacked here.
#: An asset named '<tag>.<format>' is the project's source at that tag rather
#: than a link on the release. The API also serves a plain '.tar', which is not
#: among the formats :func:`siliconcompiler.package.https._archive_formats`
#: reads.
_SOURCE_FORMATS = ("tar.gz", "tar.bz2", "zip")


def get_resolver() -> Dict[str, Type["GitlabResolver"]]:
    """
    Returns a dictionary mapping GitLab URI schemes to the GitlabResolver class.

    This function is used by the resolver system to discover and register this
    resolver for handling `gitlab` and `gitlab+private` protocols.

    Returns:
        dict: A dictionary mapping scheme names to the GitlabResolver class.
    """
    return {
        "gitlab": GitlabResolver,
        "gitlab+private": GitlabResolver
    }


class GitlabResolver(HTTPResolver):
    """
    A release asset or source archive from a GitLab project.

    Format:
        ``gitlab://<host>/<namespace...>/<project>/<tag>/<asset>``

        The host is always written out, ``gitlab.com`` included. The project may
        sit in nested groups (``group/subgroup/project``): the last two segments
        are the tag and the asset, and everything before them is the project's
        path. A tag or asset name holding a ``/`` writes it as ``%2F``. An empty
        tag (``.../<project>//<asset>``) means the latest release.

        An asset named ``<tag>.tar.gz``, ``<tag>.tar.bz2`` or ``<tag>.zip`` is
        the project's source at that tag, downloaded through the API and
        unwrapped from the directory GitLab packs it in. Any other name is a
        link on the release to an archive, unpacked as its author published it.

    Tag:
        Required, but it does not choose what is fetched: the tag in the URL
        does. It keys the cache entry along with the URL, so with an empty tag
        in the URL, changing this one is what fetches the latest release again.

    Authentication:
        A project that cannot be read anonymously is read with a token, sent as
        ``Authorization: Bearer <token>`` and only ever to the GitLab host
        itself. gitlab.com takes ``GITLAB_TOKEN`` or ``GL_TOKEN``, then
        ``GIT_TOKEN``; a self-hosted instance takes ``GIT_TOKEN`` alone, so that
        a host which only calls itself GitLab is never handed the ambient
        ``GITLAB_TOKEN``. ``gitlab+private://`` skips the anonymous attempt. The
        URL cannot carry a credential of its own.

    Example:
        .. code-block:: python

            design.set_dataroot("ip", "gitlab://gitlab.com/org/ip/v1.0/v1.0.tar.gz",
                                tag="v1.0")
    """

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        """
        Initializes the GitlabResolver.
        """
        super().__init__(name, schema, source, reference)

        self.__url = None
        self.__public = None
        self.__source_archive = False

        url = self.urlparse
        if url.username is not None or url.password is not None:
            raise ValueError(
                f"'{self._masked_uri(self.source)}' carries a credential: a gitlab:// "
                "source takes its token from the environment instead, such as "
                "GITLAB_TOKEN or GIT_TOKEN")

        segments = url.path.split("/")[1:]
        if not url.hostname or len(segments) < 4 or not all(segments[:-2]) \
                or not segments[-1]:
            raise ValueError(
                f"'{self.source}' is not in the proper form: "
                "gitlab://<host>/<namespace>/<project>/<tag>/<asset>")

    @property
    def gitlab_path(self) -> Tuple[str, str, str, str]:
        """
        Parses the source URL into its constituent GitLab parts.

        Each segment is percent-decoded once split off, so a tag such as
        ``release/1.0`` can be written ``release%2F1.0``.

        Returns:
            tuple: A tuple containing (host, project path, tag, asset name).
        """
        segments = [unquote(segment) for segment in self.urlparse.path.split("/")[1:]]
        return self.urlparse.netloc, "/".join(segments[:-2]), segments[-2], segments[-1]

    @property
    def __api_root(self) -> str:
        """The API URL of the project, which every request here starts from."""
        host, project, _, _ = self.gitlab_path
        return f"https://{host}/api/v4/projects/{quote(project, safe='')}"

    @property
    def download_url(self) -> str:
        """
        Determines the URL of the source archive or release asset.

        Looked up through the API the first time, then remembered.

        Returns:
            str: The direct URL to download from.

        Raises:
            DataSourceUnavailableError: If the project, the release or the asset
                is not there.
        """
        if self.__url is None:
            self.__url = self.__find_download_url()
        return self.__url

    def __find_download_url(self) -> str:
        """Works out :attr:`download_url`, deciding first whether to authenticate."""
        _, project, tag, asset = self.gitlab_path

        if self.is_private:
            self.__public = False
        else:
            # An anonymous request first: a token is only sent where one is
            # needed, and a stale token gets 401 even from a public project.
            self.__public = requests.get(self.__api_root, timeout=self.request_timeout).ok
            if not self.__public:
                self.logger.info("Could not find public project, trying private.")

        if not tag:
            tag = self.__latest_tag()
            self.logger.info(f"No release specified, using latest: {tag}")

        for fmt in _SOURCE_FORMATS:
            if asset == f"{tag}.{fmt}":
                self.__source_archive = True
                return f"{self.__api_root}/repository/archive.{fmt}?sha={quote(tag, safe='')}"

        release = self.__api_get(f"/releases/{quote(tag, safe='')}")
        for link in release.get("assets", {}).get("links", []):
            if link.get("name") == asset:
                # The link's own URL may be on any host; direct_asset_url is on
                # this one and redirects there, which drops the token on the way.
                return link.get("direct_asset_url") or link["url"]

        raise DataSourceUnavailableError(
            f"Unable to find release asset: {project}/{tag}/{asset}")

    def __latest_tag(self) -> str:
        """The tag of the project's newest release that is already out."""
        _, project, _, _ = self.gitlab_path
        # The release list rather than releases/permalink/latest, which a
        # self-hosted instance older than the endpoint does not have. Newest first.
        for release in self.__api_get("/releases", params={"per_page": 20}):
            if not release.get("upcoming_release"):
                return release["tag_name"]
        raise DataSourceUnavailableError(f"{project} has no release")

    def __api_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        The decoded answer to an API request for ``path`` under the project.

        Raises:
            DataSourceUnavailableError: If GitLab answers with one of the
                :data:`~siliconcompiler.package.https._TERMINAL_STATUSES`.
            FileNotFoundError: If it answers with any other failure.
        """
        url = f"{self.__api_root}{path}"
        headers = {}
        try:
            headers["Authorization"] = \
                f"Bearer {self._get_auth_token(self._token_prefixes(url))}"
        except ValueError:
            pass

        response = requests.get(url, headers=headers, params=params,
                                timeout=self.request_timeout)
        if not response.ok:
            status = response.status_code
            error = DataSourceUnavailableError if status in _TERMINAL_STATUSES \
                else FileNotFoundError
            raise error(f'Failed to look up {self.display_name} data source at '
                        f'{self._masked_uri(url)}. Status code: {status}')
        return response.json()

    def _token_prefixes(self, data_url: str) -> List[str]:
        if self.__public or urlparse(data_url).hostname != self.urlparse.hostname:
            # Nothing for a public project, and nothing for a release link off the
            # GitLab host: a link can point anywhere.
            return []
        if self._saas_forge(self.urlparse.hostname) == "gitlab":
            return ["GITLAB", "GL", "GIT"]
        return ["GIT"]

    def _archive_root(self, data_url: str, entries: List[str]) -> Optional[str]:
        if self.__source_archive and len(entries) == 1:
            # Named '<project>-<tag>-<commit>' by the API: taken as found, since
            # the commit is not in the URL to rebuild the name from.
            return entries[0]
        return None
