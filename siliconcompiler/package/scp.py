"""
This module provides a resolver for SCP.
"""
import shutil
import subprocess

import os.path

from typing import Dict, Type, Optional, TYPE_CHECKING

from siliconcompiler.package import RemoteResolver

if TYPE_CHECKING:
    from siliconcompiler.project import Project


def get_resolver() -> Dict[str, Type["SCPResolver"]]:
    """
    Returns a dictionary mapping SCP schemes to the SCPResolver class.

    This function is used by the resolver system to discover and register this
    resolver for handling `scp` and `https` protocols.

    Returns:
        dict: A dictionary mapping scheme names to the SCPResolver class.
    """
    return {
        "scp": SCPResolver
    }


class SCPResolver(RemoteResolver):
    """
    A resolver for fetching and unpacking data from SCP URLs.

    This class copies a directory from a remote server using SCP
    """

    def __init__(self, name: str, root: "Project", source: str, reference: Optional[str] = None):
        """
        Initializes the SCPResolver.
        """
        super().__init__(name, root, source, reference)

        self.__host = self.urlparse.netloc
        self.__host_path = self.urlparse.path

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
    def host(self) -> str:
        """
        Extracts the host from the SCP URL.

        Returns:
            str: The host part of the SCP URL.
        """
        return self.__host

    @property
    def host_path(self) -> str:
        """
        Extracts the path from the SCP URL.

        Returns:
            str: The path part of the SCP URL.
        """
        return self.__host_path

    def resolve_remote(self) -> None:
        """
        Fetches the remote archive, unpacks it, and stores it in the cache.

        Raises:
            FileNotFoundError: If the download fails.
        """
        scp = shutil.which("scp")
        if scp is None:
            raise RuntimeError("SCP command not found. Please ensure SCP is installed and "
                               "in your PATH.")

        # Construct the SCP command
        command = [
            scp,
            "-C",  # Enable compression for faster transfers
            "-r",  # Recursively copy directories
            f"{self.host}:{self.host_path}",
            self.cache_path
        ]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            for line in result.stdout.splitlines():
                self.logger.error(line)
            for line in result.stderr.splitlines():
                self.logger.error(line)
            raise FileNotFoundError("Failed to fetch data from "
                                    f"{self.host}:{self.host_path} using SCP.")
