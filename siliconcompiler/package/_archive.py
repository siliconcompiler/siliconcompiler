"""
This module unpacks the archives that remote resolvers download.

A download is identified by trying each known format on it in turn, so it works
the same for every resolver that fetches one: :mod:`~siliconcompiler.package.https`
and the resolvers built on it, and :mod:`~siliconcompiler.package.s3`.
"""
import tarfile
import zipfile

from typing import Callable, IO, List, Tuple

from siliconcompiler.package import Resolver
from siliconcompiler.package.cache import PermanentResolutionError
from siliconcompiler.utils import extract_safely, is_zstd, open_zstd_stream, \
    zstd_available, zstd_errors, zstd_unavailable_message


def extract_tar(fileobj: IO[bytes], path: str, mode: str) -> None:
    """Extracts a tar archive, applying the PEP 706 extraction filter."""
    with tarfile.open(fileobj=fileobj, mode=mode) as tar_ref:
        extract_safely(tar_ref, path)


def extract_zstd_tar(fileobj: IO[bytes], path: str) -> None:
    """Extracts a Zstandard-compressed tar archive.

    Decompression and extraction are separate steps here, rather than the single
    ``mode="r:zst"`` that Python 3.14 offers, so that one ``tarfile`` reads the
    archive on every supported release. See
    :func:`siliconcompiler.utils.open_zstd_stream` for why that matters.
    """
    with open_zstd_stream(fileobj) as stream:
        extract_tar(stream, path, "r:")


def extract_zip(fileobj: IO[bytes], path: str) -> None:
    """Extracts a zip archive."""
    with zipfile.ZipFile(fileobj) as zip_ref:
        zip_ref.extractall(path=path)


def archive_formats() -> List[Tuple[str, Callable[[IO[bytes], str], None]]]:
    """The archive formats a download may arrive in, in the order tried.

    A download is identified by attempting it, not by reading its URL, because the
    URL is under the server's control and an archive's name is free to disagree
    with its contents. Order between formats is otherwise immaterial -- each is
    ruled out by its own magic number within the first few bytes -- so the
    long-standing formats keep their long-standing precedence.

    Zstandard appears only where the bindings for it do; the format is recognized
    either way, so a download that needs them still gets an error saying so rather
    than being called invalid (see :func:`extract_archive`).

    Returns:
        list: ``(name, extract)`` pairs, where ``extract`` takes the downloaded
            stream and the destination directory.
    """
    formats: List[Tuple[str, Callable[[IO[bytes], str], None]]] = [
        ("gzip tar", lambda fileobj, path: extract_tar(fileobj, path, "r:gz")),
        ("bzip2 tar", lambda fileobj, path: extract_tar(fileobj, path, "r:bz2")),
        ("xz tar", lambda fileobj, path: extract_tar(fileobj, path, "r:xz")),
    ]
    if zstd_available():
        formats.append(("zstd tar", extract_zstd_tar))
    formats.append(("zip", extract_zip))
    return formats


def extract_archive(fileobj: IO[bytes], path: str, data_url: str) -> str:
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
    for name, extract in archive_formats():
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
