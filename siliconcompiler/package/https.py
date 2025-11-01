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

from typing import Dict, Type

from io import BytesIO
from urllib.parse import urlparse

from siliconcompiler.package import RemoteResolver


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
        "https": HTTPResolver
    }


class HTTPResolver(RemoteResolver):
    """
    A resolver for fetching and unpacking data from HTTP/HTTPS URLs.

    This class downloads a file from a URL, automatically determines if it's a
    gzipped tarball or a zip file, and extracts its contents into the local
    cache. It also includes special handling to flatten the directory structure
    of archives downloaded from GitHub.
    """

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

    def resolve_remote(self) -> None:
        """
        Fetches the remote archive, unpacks it, and stores it in the cache.

        This method downloads the file, detects the archive type (tar.gz or zip),
        and extracts it. It includes special logic to handle the extra top-level
        directory that GitHub often includes in its source archives.

        Raises:
            FileNotFoundError: If the download fails (e.g., 404 error).
        """
        data_url = self.download_url

        headers = {}
        # Use GIT_TOKEN for authentication if available, primarily for GitHub raw downloads.
        auth_token = os.environ.get('GIT_TOKEN', self.urlparse.username)
        if auth_token:
            headers['Authorization'] = f'token {auth_token}'
        # GitHub release assets require a specific Accept header.
        if "github" in data_url:
            headers['Accept'] = 'application/octet-stream'

        self.logger.info(f'Downloading {self.name} data from {data_url}')

        response = requests.get(data_url, stream=True, headers=headers)
        if not response.ok:
            raise FileNotFoundError(f'Failed to download {self.name} data source from {data_url}. '
                                    f'Status code: {response.status_code}')

        os.makedirs(self.cache_path, exist_ok=True)

        # Download content into an in-memory buffer
        fileobj = BytesIO(response.content)

        # Attempt to extract as a tarball, fall back to zip
        try:
            with tarfile.open(fileobj=fileobj, mode='r:gz') as tar_ref:
                tar_ref.extractall(path=self.cache_path)
        except tarfile.ReadError:
            fileobj.seek(0)
            try:
                with tarfile.open(fileobj=fileobj, mode='r:bz2') as tar_ref:
                    tar_ref.extractall(path=self.cache_path)
            except tarfile.ReadError:
                fileobj.seek(0)
                try:
                    with zipfile.ZipFile(fileobj) as zip_ref:
                        zip_ref.extractall(path=self.cache_path)
                except zipfile.BadZipFile:
                    raise TypeError(f"Could not extract file from {data_url}. "
                                    "File is not a valid tar.gz or zip archive.")

        # --- GitHub-specific directory flattening ---
        # GitHub archives often have a single top-level directory like 'repo-v1.0'.
        # This logic moves the contents of that directory up one level for a cleaner cache.
        if 'github' in data_url and len(os.listdir(self.cache_path)) == 1:
            # Heuristically determine the name of the top-level directory
            gh_url = urlparse(data_url)
            repo = gh_url.path.split('/')[2]

            gh_ref = gh_url.path.split('/')[-1]
            if repo.endswith('.git'):
                gh_ref = self.reference
            elif gh_ref.endswith('.tar.gz'):
                gh_ref = gh_ref[0:-7]
            elif gh_ref.endswith('.tgz'):
                gh_ref = gh_ref[0:-4]
            else:
                gh_ref = gh_ref.split('.')[0]

            if gh_ref.startswith('v'):
                gh_ref = gh_ref[1:]

            github_folder = f"{repo}-{gh_ref}"
            potential_path = os.path.join(self.cache_path, github_folder)

            if os.path.isdir(potential_path):
                # Move all files from the subdirectory to the cache root
                for data_file in os.listdir(potential_path):
                    shutil.move(os.path.join(potential_path, data_file), self.cache_path)
                # Clean up the now-empty directory
                os.rmdir(potential_path)
