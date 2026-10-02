"""
This module provides an S3 resolver for SiliconCompiler packages.

It defines the `S3Resolver` class, which downloads an archive from Amazon S3, or
from any store that speaks its API, and unpacks it into the cache.
"""
import tempfile

import os.path

from typing import Any, Dict, Optional, Type, TYPE_CHECKING

from urllib.parse import unquote

from siliconcompiler.package import RemoteResolver
from siliconcompiler.package._archive import extract_archive
from siliconcompiler.package.cache import DataSourceUnavailableError, PermanentResolutionError

if TYPE_CHECKING:
    from botocore.exceptions import ClientError
    from siliconcompiler.project import Project


def get_resolver() -> Dict[str, Type["S3Resolver"]]:
    """
    Returns a dictionary mapping S3 URI schemes to the S3Resolver class.

    This function is used by the resolver system to discover and register this
    resolver for handling `s3` and `s3+private` protocols.

    Returns:
        dict: A dictionary mapping scheme names to the S3Resolver class.
    """
    return {
        "s3": S3Resolver,
        "s3+private": S3Resolver
    }


class S3Resolver(RemoteResolver):
    """
    A resolver for fetching and unpacking an archive stored in S3.

    The expected source URI format is:
    `s3://<bucket>/<key>`

    The key names one archive object, in any format
    :func:`~siliconcompiler.package._archive.archive_formats` reads. A source
    ending in ``/`` names a prefix instead, and the object is
    ``<prefix>/<reference>.tar.gz``, as for an ``https://`` source. A ``?`` or
    ``#`` in a key is written ``%3F`` or ``%23``.

    Any store that speaks the S3 API works -- MinIO, Ceph, Cloudflare R2 and the
    rest -- once boto3 is pointed at it with ``AWS_ENDPOINT_URL_S3`` or
    ``AWS_ENDPOINT_URL``. Credentials come from boto3's own chain: environment
    variables, ``~/.aws``, ``AWS_PROFILE``, SSO, and an instance or task role.
    Never from the source, which takes no userinfo. With no credentials found the
    request goes unsigned, which reads a public bucket. The ``s3+private`` scheme
    requires credentials instead.

    boto3 is not installed with SiliconCompiler: it comes with the ``s3`` extra,
    ``pip install siliconcompiler[s3]``.
    """

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        """
        Initializes the S3Resolver.
        """
        super().__init__(name, schema, source, reference)

        url = self.urlparse
        if url.username is not None or url.password is not None:
            raise ValueError(
                f"'{self._masked_uri(self.source)}' carries a credential: an s3:// "
                "source takes its credentials from the AWS chain instead, such as "
                "AWS_PROFILE or AWS_ACCESS_KEY_ID")

        if not url.netloc or ":" in url.netloc:
            raise ValueError(
                f"'{self.source}' is not in the proper form: s3://<bucket>/<key>. "
                "A store other than AWS is chosen with AWS_ENDPOINT_URL_S3, not a "
                "host in the source.")

        if url.query or url.fragment:
            raise ValueError(
                f"'{self._masked_uri(self.source)}' has a query or fragment, which an "
                "s3:// source does not take: write a '?' or '#' in the key as %3F or %23")

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
    def bucket(self) -> str:
        """The bucket the object is in."""
        return self.urlparse.netloc

    @property
    def key(self) -> str:
        """
        The object's key: the source's path, or ``<reference>.tar.gz`` under it
        if the path is a prefix ending in ``/``.

        Returns:
            str: The key, percent-decoded.
        """
        url = self.urlparse
        # urlparse splits ';params' off the last segment, which in a key is text.
        path = f"{url.path};{url.params}" if url.params else url.path
        path = path[1:]
        if not path or path.endswith("/"):
            path = f"{path}{self.reference}.tar.gz"
        return unquote(path)

    @property
    def download_url(self) -> str:
        """
        The object as an ``s3://`` URL, with the key the reference completes.

        Returns:
            str: The URL of the object downloaded.
        """
        return f"s3://{self.bucket}/{self.key}"

    def _client(self) -> Any:
        """
        A boto3 client for S3, signed with the credentials boto3 finds, or
        unsigned if it finds none.

        Returns:
            botocore.client.BaseClient: The client.

        Raises:
            PermanentResolutionError: If boto3 is not installed, which no retry
                can change.
            ValueError: If the source is ``s3+private`` and no credentials are
                found.
        """
        try:
            import boto3
            from botocore import UNSIGNED
            from botocore.config import Config
        except ImportError:
            raise PermanentResolutionError(
                f"Unable to fetch {self.display_name} from {self.download_url}: an "
                "s3:// source needs boto3. Install it with: "
                "pip install siliconcompiler[s3]") from None

        session = boto3.session.Session()
        config = Config(connect_timeout=self.request_timeout,
                        read_timeout=self.request_timeout)
        if session.get_credentials() is None:
            if self.is_private:
                raise ValueError(
                    f"Unable to fetch {self.display_name} from {self.download_url}: "
                    "an s3+private:// source needs AWS credentials, and none were "
                    "found. Set them as for the AWS CLI: AWS_PROFILE, "
                    "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, "
                    "~/.aws/credentials, or an instance role.")
            self.logger.info("No AWS credentials found, sending an unsigned request.")
            config = config.merge(Config(signature_version=UNSIGNED))

        return session.client("s3", config=config)

    def __download_error(self, error: "ClientError", signed: bool) -> FileNotFoundError:
        """
        The error to raise for a download S3 refused.

        Decided by the HTTP status, not the error code: a ``HEAD`` has no body to
        carry a code in, so a missing key can arrive as ``404`` rather than
        ``NoSuchKey``.

        Args:
            error (botocore.exceptions.ClientError): What boto3 raised.
            signed (bool): Whether the request was signed.

        Returns:
            FileNotFoundError: A
            :class:`~siliconcompiler.package.cache.DataSourceUnavailableError`
            for a 404, which settles the source, else a plain FileNotFoundError,
            which a retry may get past. A 403 stays retryable, as it does for
            ``https://``: it turns into a 200 once credentials are granted.
        """
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        code = error.response.get("Error", {}).get("Code")
        message = (f"Failed to download {self.display_name} data source from "
                   f"{self.download_url}. Status code: {status}")
        if code and code != str(status):
            message += f" ({code})"
        if status == 404:
            return DataSourceUnavailableError(message)
        if status == 403:
            message += (". S3 also answers 403 for a key that does not exist, to "
                        "a caller who may not list the bucket")
            if not signed:
                message += ". No AWS credentials were found, so the request was unsigned"
        return FileNotFoundError(message)

    def resolve_remote(self) -> None:
        """
        Fetches the archive, unpacks it, and stores it in the cache.

        The archive is downloaded to a temporary file in the cache directory, not
        into memory, since a PDK archive can run to gigabytes.

        Raises:
            FileNotFoundError: If the download fails. A 404 raises the
                :class:`~siliconcompiler.package.cache.DataSourceUnavailableError`
                subclass, so the source is abandoned rather than re-requested;
                every other status, 403 included, stays retryable.
            PermanentResolutionError: If boto3 is not installed, or the archive
                is in a format this environment lacks the bindings to unpack.
            TypeError: If the object is in no archive format known here.
            ValueError: If the source is ``s3+private`` and no credentials are
                found.
        """
        client = self._client()
        # boto3 is known to be importable once there is a client.
        from botocore import UNSIGNED
        from botocore.exceptions import ClientError
        signed = client.meta.config.signature_version is not UNSIGNED

        data_url = self.download_url
        self.logger.info(f'Downloading {self.display_name} data from {data_url}')

        cache_path = self.cache_path
        # Beside the cache rather than in the system's temporary directory, which
        # is often a RAM-backed tmpfs smaller than a PDK.
        with tempfile.TemporaryFile(dir=self.cache_dir) as fileobj:
            try:
                client.download_fileobj(self.bucket, self.key, fileobj)
            except ClientError as e:
                raise self.__download_error(e, signed) from e

            os.makedirs(cache_path, exist_ok=True)
            archive_format = extract_archive(fileobj, cache_path, data_url)
        self.logger.debug(f'Unpacked {self.display_name} data as a {archive_format} archive')
