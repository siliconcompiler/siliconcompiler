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
    resolver for handling `scp`.

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

        self.__host = None
        self.__host_path = None
        self.__host_port = ...

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
        if self.__host is None:
            netloc = self.urlparse.netloc
            if ':' in netloc:
                self.__host, _ = netloc.rsplit(':', 1)
            else:
                self.__host = netloc

        return self.__host

    @property
    def host_path(self) -> str:
        """
        Extracts the path from the SCP URL.

        Returns:
            str: The path part of the SCP URL.
        """
        if self.__host_path is None:
            self.__host_path = self.urlparse.path

        return self.__host_path

    @property
    def host_port(self) -> Optional[int]:
        """
        Extracts the port from the SCP URL, if specified.

        Returns:
            int or None: The port number if specified, otherwise None.
        """
        if self.__host_port is ...:
            netloc = self.urlparse.netloc
            if ':' in netloc:
                _, port_str = netloc.rsplit(':', 1)
                try:
                    self.__host_port = int(port_str)
                except ValueError:
                    self.__host_port = None
            else:
                self.__host_port = None
        return self.__host_port

    def resolve_remote(self) -> None:
        """
        Fetches the remote archive, unpacks it, and stores it in the cache.

        Raises:
            RuntimeError: If the SCP command is not found.
            FileNotFoundError: If the remote path cannot be fetched.
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
        ]

        # Add port flag if non-default port is specified
        port = self.host_port
        if port is not None:
            command.extend(["-P", str(port)])

        # Add source and destination
        command.extend([
            f"{self.host}:{self.host_path}",
            self.cache_path
        ])

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            for line in result.stdout.splitlines():
                self.logger.error(line)
            for line in result.stderr.splitlines():
                self.logger.error(line)
            raise FileNotFoundError("Failed to fetch data from "
                                    f"{self.host}:{self.host_path} using SCP.")
