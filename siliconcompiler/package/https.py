"""
This module provides a generic HTTP/HTTPS resolver for SiliconCompiler packages.

It defines the `HTTPResolver` class, which is responsible for downloading
and unpacking archives (TAR or ZIP) from a given URL.

`HTTPResolver` handles no particular host itself. One that needs more -- a
header, its own tokens, or an archive unwrapped -- gets a subclass overriding
`HTTPResolver._get_headers`, `HTTPResolver._token_prefixes` and
`HTTPResolver._archive_root`, which `HTTPResolver.subresolver` hands that host's
URLs to.
"""
import requests
import shutil

import os.path

from typing import Dict, List, Optional, Type

from io import BytesIO
from urllib.parse import ParseResult, urljoin, urlparse

from siliconcompiler.package import FetchRefused, RemoteResolver, Resolver, \
    current_fetch_policy
from siliconcompiler.package._archive import extract_archive
from siliconcompiler.package.cache import DataSourceUnavailableError

#: HTTP statuses that answer the request completely enough that asking again can
#: only collect the same answer: the data is not there (404, 410) or the request
#: itself is one no server will accept (400, 405, 414, 451).
#:
#: An allowlist rather than "any 4xx", because plenty of 4xx responses do change:
#: 408 and 429 ask to be retried outright, 409/421/423/425 describe a passing
#: condition, and 401/403 turn into a 200 as soon as a token is granted -- GitHub
#: also answers 403 for rate limiting. Since the attempt budget is shared by cache
#: ID, which covers only the source and its reference, retiring one of those would
#: also block a later resolver that does have credentials. A 5xx stays retryable
#: too: a server having a bad minute may not be having a bad hour.
_TERMINAL_STATUSES = (400, 404, 405, 410, 414, 451)

# How many redirects a download under a fetch policy follows. GitHub's archive
# takes one.
_MAX_REDIRECTS = 5


def _no_auth(request: requests.PreparedRequest) -> requests.PreparedRequest:
    """
    A requests auth hook that adds nothing.

    Passed where no credential may be sent: given no hook, requests takes a
    username and password from the URL and sends them as Basic auth.
    """
    return request


def get_resolver() -> Dict[str, Type["HTTPResolver"]]:
    """
    Returns a dictionary mapping HTTP schemes to the HTTPResolver class.

    This function is used by the resolver system to discover and register this
    resolver for handling `http` and `https` protocols.

    Returns:
        dict: A dictionary mapping scheme names to the HTTPResolver class.
    """
    return {
        "http": HTTPResolver,
        "https": HTTPResolver,
        "http+private": HTTPResolver,
        "https+private": HTTPResolver
    }


class HTTPResolver(RemoteResolver):
    """
    An archive downloaded over HTTP or HTTPS.

    Format:
        ``https://<host>/<path>`` or ``http://<host>/<path>``

        The download is unpacked into the cache. Its format is read from its
        contents rather than its name: a tar compressed with gzip, bzip2, xz or
        Zstandard, or a zip. A URL on a GitHub host is handled as GitHub's
        archives are, see :ref:`resolver-githubarchive`.

    Tag:
        Appended to a URL that ends in ``/`` as ``<tag>.tar.gz``:
        ``https://example.com/ip/`` with the tag ``v1.0`` downloads
        ``https://example.com/ip/v1.0.tar.gz``. A URL naming its file outright
        uses the tag only to key its cache entry.

    Authentication:
        A username and password in the URL are sent as Basic auth, and a
        username alone as ``Authorization: Bearer <username>``. Otherwise the
        token is read from ``HTTPS_TOKEN``, then ``HTTP_TOKEN``, and sent as a
        Bearer token. A plain ``http://`` URL is never sent a credential, since
        it would cross the network in cleartext.

    Example:
        .. code-block:: python

            design.set_dataroot("ip", "https://example.com/ip/", tag="v1.0")
    """

    @classmethod
    def subresolver(cls, url: ParseResult) -> Type[Resolver]:
        """
        The resolver for ``url``: GitHub's for an archive on a GitHub host, else
        this one.

        Only the resolver registered for the HTTP schemes chooses. A subclass is
        registered for a scheme of its own, ``github://`` for one, and keeps it:
        the hosts in such a URL are not web hosts -- ``github://github/...``
        names the owner ``github`` -- so matching them here would hand the URL
        to the wrong class.

        Args:
            url (urllib.parse.ParseResult): The parsed source URI.

        Returns:
            type: The resolver class to use.
        """
        if cls is not HTTPResolver:
            return cls

        # Imported here: the github module imports this one.
        from siliconcompiler.package.github import GithubArchiveResolver
        if GithubArchiveResolver.claims(url):
            return GithubArchiveResolver
        return cls

    def check_cache(self) -> bool:
        """
        Checks if the data has already been cached.

        For this resolver, the cache is considered valid if the target cache
        directory simply exists.

        Returns:
            bool: True if the cache path exists, False otherwise.
        """
        return os.path.exists(self.cache_path)

    @property
    def download_url(self) -> str:
        """
        Constructs the final download URL.

        If the source URL ends with a '/', it appends the reference
        (e.g., version) and a `.tar.gz` extension.

        Returns:
            str: The fully-formed URL to download from.
        """
        data_url = self.source
        if data_url.endswith('/'):
            data_url = f"{data_url}{self.reference}.tar.gz"
        return data_url

    def _get_headers(self) -> Dict[str, str]:
        """
        Constructs the HTTP headers for the download request.

        The base adds no credential: :meth:`resolve_remote` looks one up, but
        only if the headers returned here carry no ``Authorization`` of their
        own, so a subclass that sets one decides the credential itself.

        Returns:
            dict: A dictionary of HTTP headers to include in the download request.
        """
        return {}

    def _token_prefixes(self, data_url: str) -> List[str]:
        """
        The environment variable prefixes a credential for ``data_url`` is
        looked up under, most preferred first (see
        :meth:`~siliconcompiler.package.RemoteResolver._get_auth_token`).

        The base offers only the generic opt-ins, which any host may receive. A
        subclass adding a service's own variables has to make sure the host is
        that service's: those are often set ambiently, as ``GITHUB_TOKEN`` is in
        every GitHub Actions job.

        Args:
            data_url (str): The URL about to be downloaded.

        Returns:
            list: The prefixes, such as ``["HTTPS", "HTTP"]``.
        """
        return ["HTTPS", "HTTP"]

    def _archive_root(self, data_url: str, entries: List[str]) -> Optional[str]:
        """
        The directory the archive from ``data_url`` wraps its contents in, if
        any.

        Asked once the archive is unpacked. When it unpacked to that directory
        and nothing else, the directory's contents are moved up, so the cache
        root is the archive's own root. The base expects no wrapper.

        Args:
            data_url (str): The URL the archive was downloaded from.
            entries (list): The names the archive unpacked to, at its top level.

        Returns:
            str or None: The directory's name, or None to leave the archive as
            it unpacked.
        """
        return None

    def resolve_remote(self) -> None:
        """
        Fetches the remote archive, unpacks it, and stores it in the cache.

        This method downloads the file, detects the archive type (a tar compressed
        with gzip, bzip2, xz or Zstandard, or a zip), and extracts it, moving up
        the contents of the directory :meth:`_archive_root` names.

        A username and password in the URL are sent as Basic auth. Otherwise a
        token -- a username alone in the URL, else the first found under
        :meth:`_token_prefixes` -- is sent as ``Authorization: Bearer <token>``.
        A plain ``http://`` download sends no credential at all, since it would
        cross the network in cleartext.

        Raises:
            FileNotFoundError: If the download fails. One of the
                :data:`_TERMINAL_STATUSES` raises the
                :class:`~siliconcompiler.package.cache.DataSourceUnavailableError`
                subclass, so the source is abandoned rather than re-requested;
                every other status, including 401 and 403, stays retryable.
            TypeError: If what arrives is in no archive format known here.
            PermanentResolutionError: If it arrives in one this environment lacks
                the bindings to unpack, which no retry can change.
        """
        data_url = self.download_url
        url = urlparse(data_url)

        policy = current_fetch_policy()
        if policy is not None:
            import tempfile

            # The URL asked for, not the last hop: GitHub's flattening below
            # reads the repository and ref out of it.
            response = self._get_under_policy(policy, data_url)
            if not response.ok:
                self._extract_response(response, data_url)
            # Streamed to disk against the policy's ceiling, not held in memory.
            with tempfile.TemporaryFile() as body:
                size = 0
                for chunk in response.iter_content(1024 * 1024):
                    size += len(chunk)
                    if policy.max_bytes and size > policy.max_bytes:
                        raise FetchRefused(f"{self.display_name}: larger than "
                                           f"{policy.max_bytes} bytes")
                    body.write(chunk)
                body.seek(0)
                self._extract_response(response, data_url, body)
            return

        headers = self._get_headers()
        # A password in the URL makes it Basic auth, which requests builds from the
        # URL itself and puts over any header set here.
        basic_auth = url.password is not None
        if "Authorization" not in headers and not basic_auth:
            auth_token = self.urlparse.username
            if not auth_token:
                try:
                    auth_token = self._get_auth_token(self._token_prefixes(data_url))
                except ValueError:
                    pass
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'

        auth = None
        if url.scheme == "http" and (basic_auth or "Authorization" in headers):
            self.logger.warning(
                f'Not sending a credential for {self.display_name}: '
                f'{Resolver._masked_uri(data_url)} is plain http://, which would '
                'send it in cleartext. Use https:// to authenticate.')
            headers.pop("Authorization", None)
            auth = _no_auth

        self.logger.info(f'Downloading {self.display_name} data from '
                         f'{Resolver._masked_uri(data_url)}')

        response = requests.get(data_url, stream=True, headers=headers, auth=auth,
                                timeout=self.request_timeout)
        self._extract_response(response, data_url)

    def _get_under_policy(self, policy, url: str):
        """
        The response for ``url`` under a :class:`~siliconcompiler.package.FetchPolicy`:
        nothing sent but the resolver's own headers, and every redirect hop
        checked before it is followed. Returns the response.
        """
        if urlparse(url).username or urlparse(url).password:
            raise FetchRefused(f"{self.display_name}: the source URL carries a credential")

        session = requests.Session()
        # No proxy, no .netrc and no CA override from the environment: nothing
        # of this process's is sent on the source's behalf.
        session.trust_env = False
        headers = {name: value for name, value in self._get_headers().items()
                   if name.lower() != "authorization"}
        for _ in range(_MAX_REDIRECTS + 1):
            policy.check_url(url)
            response = session.get(url, stream=True, headers=headers,
                                   allow_redirects=False, timeout=policy.timeout)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise FetchRefused(f"{self.display_name}: redirected without saying where")
                url = urljoin(url, location)
                continue
            return response
        raise FetchRefused(f"{self.display_name}: too many redirects")

    def _extract_response(self, response, data_url: str, fileobj=None) -> None:
        """Unpack a download -- ``fileobj`` where it is already on disk -- into
        the cache, or raise for what it answered."""
        if not response.ok:
            status = response.status_code
            error = DataSourceUnavailableError if status in _TERMINAL_STATUSES \
                else FileNotFoundError
            error = error(f'Failed to download {self.display_name} data source from '
                          f'{Resolver._masked_uri(data_url)}. Status code: {status}')
            # What the source answered, for a caller deciding whether to retry.
            error.status = status
            raise error

        os.makedirs(self.cache_path, exist_ok=True)

        # Download content into an in-memory buffer
        if fileobj is None:
            fileobj = BytesIO(response.content)

        archive_format = extract_archive(fileobj, self.cache_path, data_url)
        self.logger.debug(f'Unpacked {self.display_name} data as a {archive_format} archive')

        entries = os.listdir(self.cache_path)
        root = self._archive_root(data_url, entries)
        root_path = os.path.join(self.cache_path, root) if root else None
        if root and entries == [root] and os.path.isdir(root_path):
            for data_file in os.listdir(root_path):
                shutil.move(os.path.join(root_path, data_file), self.cache_path)
            os.rmdir(root_path)
