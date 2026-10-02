"""
This module provides a generic HTTP/HTTPS resolver for SiliconCompiler packages.

It defines the `HTTPResolver` class, which is responsible for downloading
and unpacking archives (TAR or ZIP) from a given URL.
"""
import requests
import shutil
import tarfile
import zipfile

import os.path

from typing import Callable, Dict, IO, List, Optional, Tuple, Type

from io import BytesIO
from urllib.parse import ParseResult, urlparse

from siliconcompiler.package import RemoteResolver, Resolver
from siliconcompiler.package.cache import DataSourceUnavailableError, PermanentResolutionError
from siliconcompiler.utils import is_zstd, open_zstd_stream, tar_extract_kwargs, \
    zstd_available, zstd_errors, zstd_unavailable_message

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


def _no_auth(request: requests.PreparedRequest) -> requests.PreparedRequest:
    """
    A requests auth hook that adds nothing.

    Passed where no credential may be sent: given no hook, requests takes a
    username and password from the URL and sends them as Basic auth.
    """
    return request


def _extract_tar(fileobj: IO[bytes], path: str, mode: str) -> None:
    """Extracts a tar archive, applying the PEP 706 extraction filter."""
    with tarfile.open(fileobj=fileobj, mode=mode) as tar_ref:
        tar_ref.extractall(path=path, **tar_extract_kwargs())


def _extract_zstd_tar(fileobj: IO[bytes], path: str) -> None:
    """Extracts a Zstandard-compressed tar archive.

    Decompression and extraction are separate steps here, rather than the single
    ``mode="r:zst"`` that Python 3.14 offers, so that one ``tarfile`` reads the
    archive on every supported release. See
    :func:`siliconcompiler.utils.open_zstd_stream` for why that matters.
    """
    with open_zstd_stream(fileobj) as stream:
        _extract_tar(stream, path, "r:")


def _extract_zip(fileobj: IO[bytes], path: str) -> None:
    """Extracts a zip archive."""
    with zipfile.ZipFile(fileobj) as zip_ref:
        zip_ref.extractall(path=path)


def _archive_formats() -> List[Tuple[str, Callable[[IO[bytes], str], None]]]:
    """The archive formats an HTTP download may arrive in, in the order tried.

    A download is identified by attempting it, not by reading its URL, because the
    URL is under the server's control and an archive's name is free to disagree
    with its contents. Order between formats is otherwise immaterial -- each is
    ruled out by its own magic number within the first few bytes -- so the
    long-standing formats keep their long-standing precedence.

    Zstandard appears only where the bindings for it do; the format is recognized
    either way, so a download that needs them still gets an error saying so rather
    than being called invalid (see :func:`_extract_archive`).

    Returns:
        list: ``(name, extract)`` pairs, where ``extract`` takes the downloaded
            stream and the destination directory.
    """
    formats: List[Tuple[str, Callable[[IO[bytes], str], None]]] = [
        ("gzip tar", lambda fileobj, path: _extract_tar(fileobj, path, "r:gz")),
        ("bzip2 tar", lambda fileobj, path: _extract_tar(fileobj, path, "r:bz2")),
        ("xz tar", lambda fileobj, path: _extract_tar(fileobj, path, "r:xz")),
    ]
    if zstd_available():
        formats.append(("zstd tar", _extract_zstd_tar))
    formats.append(("zip", _extract_zip))
    return formats


def _extract_archive(fileobj: IO[bytes], path: str, data_url: str) -> str:
    """Unpacks a downloaded archive, identifying its format by trial.

    Args:
        fileobj (IO[bytes]): The downloaded archive, open and seekable.
        path (str): The directory to extract into.
        data_url (str): Where the archive came from, for error messages.

    Returns:
        str: The name of the format that read the archive.

    Raises:
        PermanentResolutionError: If the archive is Zstandard and this environment
            has no bindings to read it with. Settled rather than transient: the
            download worked and what is missing is local, so retrying would spend a
            second full transfer -- hundreds of megabytes, for a PDK artifact -- to
            re-learn that a package is not installed.
        TypeError: If the archive is in no format known here.
        tarfile.FilterError: If the extraction filter refuses a member.
    """
    for name, extract in _archive_formats():
        fileobj.seek(0)
        try:
            extract(fileobj, path)
        except (tarfile.ReadError, zipfile.BadZipFile, *zstd_errors()):
            # Not this format: the next one gets the same bytes from the start.
            continue
        return name

    fileobj.seek(0)
    header = fileobj.read(8)
    if not zstd_available() and is_zstd(header):
        raise PermanentResolutionError(
            f"Could not extract file from {Resolver._masked_uri(data_url)}. "
            f"{zstd_unavailable_message()}")

    raise TypeError(f"Could not extract file from {Resolver._masked_uri(data_url)}. "
                    "File is not a valid tar (gzip, bzip2, xz or zstd) or zip archive.")


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
    A resolver for fetching and unpacking data from HTTP/HTTPS URLs.

    This class downloads a file from a URL, determines from its contents whether
    it is a tarball (gzip, bzip2, xz or Zstandard compressed) or a zip file, and
    extracts it into the local cache.

    It handles no particular host itself. One that needs more -- a header, its
    own tokens, or an archive unwrapped -- gets a subclass overriding
    :meth:`_get_headers`, :meth:`_token_prefixes` and :meth:`_archive_root`,
    which :meth:`subresolver` hands that host's URLs to.
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

        response = requests.get(data_url, stream=True, headers=headers, auth=auth)
        if not response.ok:
            status = response.status_code
            error = DataSourceUnavailableError if status in _TERMINAL_STATUSES \
                else FileNotFoundError
            raise error(f'Failed to download {self.display_name} data source from '
                        f'{Resolver._masked_uri(data_url)}. Status code: {status}')

        os.makedirs(self.cache_path, exist_ok=True)

        # Download content into an in-memory buffer
        fileobj = BytesIO(response.content)

        archive_format = _extract_archive(fileobj, self.cache_path, data_url)
        self.logger.debug(f'Unpacked {self.display_name} data as a {archive_format} archive')

        entries = os.listdir(self.cache_path)
        root = self._archive_root(data_url, entries)
        root_path = os.path.join(self.cache_path, root) if root else None
        if root and entries == [root] and os.path.isdir(root_path):
            for data_file in os.listdir(root_path):
                shutil.move(os.path.join(root_path, data_file), self.cache_path)
            os.rmdir(root_path)
