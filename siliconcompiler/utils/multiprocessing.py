import atexit
import contextlib
import logging
import multiprocessing
import sys
import tempfile
import threading
import warnings

import os.path

from typing import Iterator, Union, Optional

from datetime import datetime
from logging.handlers import QueueHandler
from multiprocessing.context import BaseContext
from multiprocessing.managers import SyncManager, RemoteError

from siliconcompiler.utils.settings import SettingsManager
from siliconcompiler.utils import default_sc_path, default_sc_system_path

from siliconcompiler.report.dashboard.cli.board import Board


def get_process_context() -> BaseContext:
    """Returns the multiprocessing context used to launch scheduler workers.

    SiliconCompiler launches node workers and the run-check pool by handing
    them an already-configured, non-picklable object graph (the node with its
    log pipe attached, inherited logger handlers, etc.) and expects unguarded
    module-level ``proj.run()`` scripts to work. Both of those require the
    ``fork`` start method: ``spawn``/``forkserver`` re-import ``__main__`` (so
    an unguarded script recurses into the bootstrapping error) and cannot
    inherit the pre-attached pipe.

    We therefore pin ``fork`` explicitly on Linux rather than relying on the
    interpreter default, which changed to ``forkserver`` in Python 3.14.

    Everywhere else we pin ``spawn``. Note this is deliberately keyed on the
    platform, not on ``"fork" in get_all_start_methods()``: fork *is* available
    on macOS, but it is unsafe there with threads (SC runs a logging
    ``QueueListener`` and the dashboard board on threads), which is why CPython
    itself defaults macOS to ``spawn``. Windows has no fork at all. On those
    platforms callers must guard scripts with ``if __name__ == "__main__"``, as
    has always been required.
    """
    if sys.platform.startswith("linux"):
        return multiprocessing.get_context("fork")
    return multiprocessing.get_context("spawn")


@contextlib.contextmanager
def forking() -> Iterator[None]:
    """Context manager wrapping a deliberate ``fork`` of the current process.

    SiliconCompiler pins the ``fork`` start method on Linux (see
    :func:`get_process_context`) while running a logging ``QueueListener`` and
    the dashboard board on threads. Every worker launch therefore trips
    CPython's "This process is multi-threaded, use of fork() may lead to
    deadlocks in the child" ``DeprecationWarning`` (emitted by ``os.fork`` since
    Python 3.12). The fork paths are deliberately engineered to be fork-safe, so
    silence that warning at the point of the fork rather than leaking it onto
    downstream users' consoles or forcing them to configure a global filter.

    Only the fork-with-threads warning is suppressed; any other warning raised
    while forking still propagates.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".* is multi-threaded, use of fork\(\) may lead to deadlocks in the child",
            category=DeprecationWarning)
        yield


class _ManagerSingleton(type):
    """
    A metaclass to enforce the singleton pattern on any class that uses it.

    This ensures that only one instance of the target class is ever created
    within the application's lifecycle. It uses a lock to make the
    instantiation process thread-safe.

    Attributes:
        _instances (dict): A dictionary to store singleton instances, mapping
            class objects to their single instance.
        _lock (threading.Lock): A lock to prevent race conditions during
            the first instantiation.
    """
    _instances = {}
    # A threading.Lock (not multiprocessing.Lock) is sufficient and correct
    # here: the singleton registry ``_instances`` is per-process state, so this
    # only needs to guard threads within a single interpreter. Using a
    # multiprocessing.Lock would allocate a POSIX named semaphore in every
    # process that imports this module (including every spawned scheduler
    # worker), which the resource_tracker then reports as "leaked" when a
    # worker is terminated before it can unlink the semaphore.
    _lock = threading.Lock()

    @staticmethod
    def has_cls(mcls):
        """
        Checks if a singleton instance exists for the given class.

        Args:
            cls (type): The class to check.

        Returns:
            bool: True if an instance exists, False otherwise.
        """
        return mcls in _ManagerSingleton._instances

    @staticmethod
    def remove_cls(mcls):
        """
        Removes a class's singleton instance from the registry.

        This is useful for cleanup, especially in testing scenarios where
        a fresh instance is needed.

        Args:
            cls (type): The class whose instance should be removed.
        """
        if not _ManagerSingleton.has_cls(mcls):
            return

        with _ManagerSingleton._lock:
            if mcls in _ManagerSingleton._instances:
                del _ManagerSingleton._instances[mcls]

    def __call__(cls, *args, **kwargs):
        """
        Handles the instantiation of the class using a double-checked lock.

        If an instance of the class does not already exist, it creates one
        and stores it. Subsequent calls will return the existing instance.
        A special '_init_singleton' method is called on the first creation.
        """
        if not _ManagerSingleton.has_cls(cls):
            with _ManagerSingleton._lock:
                if cls not in _ManagerSingleton._instances:
                    instance = super(_ManagerSingleton, cls).__call__(*args, **kwargs)
                    _ManagerSingleton._instances[cls] = instance
                    # Custom initializer for the singleton instance
                    instance._init_singleton()
        return _ManagerSingleton._instances[cls]


class MPManager(metaclass=_ManagerSingleton):
    """
    A singleton manager for handling multiprocessing resources in SiliconCompiler.

    This class provides centralized, thread-safe access to shared resources
    like a logger, a multiprocessing.Manager, and a dashboard Board instance.
    It is designed to be instantiated once and accessed globally.
    """
    __ENABLE_LOGGER: bool = True
    __address: Union[None, str] = None
    __authkey: bytes = b'siliconcompiler-manager-authkey'  # arbitrary authkey value

    def __init__(self):
        """
        Initializes the MPManager.

        Note: The actual setup logic is in _init_singleton, which is called
        automatically by the _ManagerSingleton metaclass upon first instantiation.
        """
        pass

    def _init_singleton(self) -> None:
        """
        Performs the one-time initialization of the singleton instance.

        This method sets up the start time, error flag, logger,
        multiprocessing manager, and registers the cleanup function (`stop`)
        to be called on program exit.
        """
        self.__start = datetime.now()
        self.__error = False

        # Parent logger setup
        now_file = self.__start.strftime("%Y-%m-%d-%H-%M-%S-%f")
        self.__logfile = os.path.join(tempfile.gettempdir(),
                                      "siliconcompiler",
                                      f"{now_file}_{id(self)}.log")
        self._init_logger()

        # Manager to handle shared data between processes
        is_server = MPManager._get_manager_address() is None
        if not is_server:
            try:
                self.__manager = SyncManager(address=MPManager._get_manager_address(),
                                             authkey=MPManager.__authkey)
                self.__manager.connect()
                self.__manager_server = False
            except FileNotFoundError:  # error when address has been deleted by previous server
                self.__logger.warning("Manager address file not found; falling back to server mode")
                is_server = True  # fall back to create new manager
        if is_server:
            # Pin the start method for the manager's server process: its
            # start() launches a process, and under the Python 3.14 default
            # (forkserver) that re-imports __main__ and breaks unguarded
            # module-level proj.run() scripts. See get_process_context().
            self.__manager = SyncManager(authkey=MPManager.__authkey,
                                         ctx=get_process_context())
            with forking():
                self.__manager.start()
            MPManager._set_manager_address(self.__manager.address)
            self.__manager_server = True

        # Dashboard singleton setup
        self.__board_lock = self.__manager.Lock()
        self.__board = None

        # Settings
        self.__settings = SettingsManager(
            default_sc_path("settings.json"), self.__logger,
            system_filepath=default_sc_system_path())
        self.__transient_settings = SettingsManager(None, self.__logger)

        # Register cleanup function to run at exit
        atexit.register(MPManager.stop)

    def _init_logger(self) -> None:
        """
        Initializes the logging configuration for SiliconCompiler.

        It sets up a root logger named "siliconcompiler" and adds a file
        handler to log messages to a temporary file. The log level is
        initially set to INFO to capture the start time and then raised
        to WARNING.
        """
        # Root logger for the application
        self.__logger = logging.getLogger("siliconcompiler")
        self.__logger.propagate = False

        if self.__ENABLE_LOGGER:
            self.__logger.setLevel(logging.INFO)
            try:
                os.makedirs(os.path.dirname(self.__logfile), exist_ok=True)

                handler = logging.FileHandler(self.__logfile)
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s | %(name)s | %(levelname)s | %(message)s'))
                handler.setLevel(logging.INFO)

                self.__logger.addHandler(handler)

                now_print = self.__start.strftime("%Y-%m-%d %H:%M:%S.%f")
                self.__logger.info(f"Log started at {now_print}")

                # Reduce logging level after initial message
                handler.setLevel(logging.WARNING)
            except Exception:
                # Fails silently if logging can't be set up
                pass

    @staticmethod
    def stop() -> None:
        """
        Cleans up all managed resources as a static method.

        This method is registered with atexit to run on script termination.
        It closes logger handlers, deletes the log file if no errors occurred,
        stops the dashboard service, shuts down the multiprocessing manager,
        and finally removes the singleton instance from the registry.
        """
        if not _ManagerSingleton.has_cls(MPManager):
            return

        manager = MPManager()

        try:
            # Remove all logger handlers to release file locks
            for handler in list(manager.__logger.handlers):
                manager.__logger.removeHandler(handler)
                handler.close()

            # Remove the log file if the run was successful
            if not manager.__error:
                try:
                    os.remove(manager.__logfile)
                except:  # noqa E722
                    pass

            # Stop the dashboard service if it's running
            if manager.__board:
                try:
                    with manager.__board_lock:
                        if manager.__board:
                            manager.__board.stop()
                            manager.__board = None
                except RemoteError:
                    # Try without the lock
                    if manager.__board:
                        manager.__board.stop()
                        manager.__board = None

            if manager.__manager_server:
                # Shut down the multiprocessing manager
                MPManager.__address = None
                manager.__manager.shutdown()
        except:  # noqa E722
            # Catch everything (incl. KeyboardInterrupt) so a signal arriving
            # mid-cleanup cannot escape an atexit callback or leave the
            # singleton half-torn-down.
            pass
        finally:
            # Always run housekeeping, even if cleanup above was interrupted,
            # so a re-entry to stop() is a no-op.
            try:
                atexit.unregister(MPManager.stop)
            except:  # noqa E722
                pass
            try:
                _ManagerSingleton.remove_cls(MPManager)
            except:  # noqa E722
                pass

    @staticmethod
    def error(msg: Optional[str] = None):
        """
        Logs an error and flags the session as having an error.

        This prevents the log file from being deleted upon exit, preserving it
        for debugging.

        Args:
            msg (str, optional): The error message to log. Defaults to None.
        """
        manager = MPManager()
        if msg:
            manager.logger().error(f"Error: {msg}")
        else:
            manager.logger().error("Error occurred")
        manager.__error = True

    @staticmethod
    def get_manager() -> SyncManager:
        """
        Provides access to the shared multiprocessing.Manager instance.

        Returns:
            multiprocessing.Manager: The singleton manager instance.
        """
        return MPManager().__manager

    @staticmethod
    def get_settings() -> SettingsManager:
        """
        Provides access to the shared SettingsManager instance.

        Returns:
            SettingsManager: The singleton settings instance.
        """
        return MPManager().__settings

    @staticmethod
    def get_transient_settings() -> SettingsManager:
        """
        Provides access to the shared transient SettingsManager instance.

        Returns:
            SettingsManager: The singleton transient settings instance.
        """
        return MPManager().__transient_settings

    @staticmethod
    def get_dashboard() -> Board:
        """
        Lazily initializes and returns the singleton dashboard Board instance.

        This method ensures that the Board is only created when first requested
        and that its initialization is thread-safe.

        Returns:
            Board: The singleton dashboard Board instance.
        """
        manager = MPManager()
        if not manager.__board:
            with manager.__board_lock:
                # Double-check locking to ensure thread safety
                if not manager.__board:
                    manager.__board = Board(manager.__manager)
        return manager.__board

    @staticmethod
    def logger() -> logging.Logger:
        """
        Provides access to the shared logger instance.

        Returns:
            logging.Logger: The singleton logger instance.
        """
        return MPManager().__logger

    @staticmethod
    def _set_manager_address(address: str) -> None:
        """
        Set the address of the manager
        """
        if MPManager.__address is None:
            MPManager.__address = address

    @staticmethod
    def _get_manager_address() -> Union[None, str]:
        """
        Get the address of the manager
        """
        return MPManager.__address


class MPQueueHandler(QueueHandler):
    def enqueue(self, record):
        try:
            super().enqueue(record)
        except (BrokenPipeError, EOFError, ConnectionResetError, OSError, RemoteError):
            # The queue is no longer reachable so fail silently. This is
            # most likely happening during shutdown, when the parent's
            # SyncManager has gone away before the child finished logging.
            pass
