import atexit
import logging
import multiprocessing
import tempfile
import os.path
from datetime import datetime

from siliconcompiler.report.dashboard.cli.board import Board


class _ManagerSingleton(type):
    """
    A metaclass to enforce the singleton pattern on any class that uses it.

    This ensures that only one instance of the target class is ever created
    within the application's lifecycle. It uses a lock to make the
    instantiation process thread-safe.

    Attributes:
        _instances (dict): A dictionary to store singleton instances, mapping
            class objects to their single instance.
        _lock (multiprocessing.Lock): A lock to prevent race conditions during
            the first instantiation.
    """
    _instances = {}
    _lock = multiprocessing.Lock()

    def __call__(cls, *args, **kwargs):
        """
        Handles the instantiation of the class.

        If an instance of the class does not already exist, it creates one
        and stores it. Subsequent calls will return the existing instance.
        A special '_init_singleton' method is called on the first creation.
        """
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super(_ManagerSingleton, cls).__call__(*args, **kwargs)
                    cls._instances[cls] = instance
                    # Custom initializer for the singleton instance
                    instance._init_singleton()
        return cls._instances[cls]


class MPManager(metaclass=_ManagerSingleton):
    """
    A singleton manager for handling multiprocessing resources in SiliconCompiler.

    This class provides centralized, thread-safe access to shared resources
    like a logger, a multiprocessing.Manager, and a dashboard Board instance.
    It is designed to be instantiated once and accessed globally.
    """
    __ENABLE_LOGGER: bool = True

    def __init__(self):
        """
        Initializes the MPManager.

        Note: The actual setup logic is in _init_singleton, which is called
        automatically by the _ManagerSingleton metaclass upon first instantiation.
        """
        pass

    def _init_singleton(self):
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
        self.__manager = multiprocessing.Manager()

        # Dashboard singleton setup
        self.__board_lock = self.__manager.Lock()
        self.__board = None

        # Register cleanup function to run at exit
        atexit.register(self.stop)

    def _init_logger(self):
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

    def stop(self):
        """
        Cleans up all managed resources.

        This method is registered with atexit to run on script termination.
        It closes logger handlers, deletes the log file if no errors occurred,
        stops the dashboard service, and shuts down the multiprocessing manager.
        """
        # Remove all logger handlers to release file locks
        for handler in list(self.__logger.handlers):
            self.__logger.removeHandler(handler)
            handler.close()

        # Remove the log file if the run was successful
        if not self.__error:
            try:
                os.remove(self.__logfile)
            except:  # noqa E722
                pass

        # Stop the dashboard service if it's running
        if self.__board:
            with self.__board_lock:
                if self.__board:
                    self.__board.stop()
                    self.__board = None

        # Shut down the multiprocessing manager
        self.__manager.shutdown()

    @staticmethod
    def error(msg: str = None):
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
    def get_manager():
        """
        Provides access to the shared multiprocessing.Manager instance.

        Returns:
            multiprocessing.Manager: The singleton manager instance.
        """
        return MPManager().__manager

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
