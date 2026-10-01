import atexit
import contextlib
import logging
import sys
import tempfile
import threading
import time
import warnings
import weakref

import os.path

from typing import Iterator, Union, Optional, Tuple, TYPE_CHECKING

from datetime import datetime
from fasteners import InterProcessLock
from logging.handlers import QueueHandler

from siliconcompiler.utils import default_sc_path, default_sc_system_path


if TYPE_CHECKING:
    from multiprocessing.context import BaseContext
    from multiprocessing.managers import SyncManager

    from siliconcompiler.package.cache import PathCache
    from siliconcompiler.report.dashboard.cli.board import Board
    from siliconcompiler.utils.settings import SettingsManager


def get_process_context() -> "BaseContext":
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
    # Imported here rather than at module scope: multiprocessing and its manager
    # machinery are among the costlier imports in the tree, and nothing needs
    # them until a run actually starts.
    import multiprocessing

    if sys.platform.startswith("linux"):
        return multiprocessing.get_context("fork")
    return multiprocessing.get_context("spawn")


@contextlib.contextmanager
def forking() -> Iterator[None]:
    """Context manager wrapping a deliberate ``fork`` of the current process.

    SiliconCompiler pins the ``fork`` start method on Linux (see
    :func:`get_process_context`) while running a logging ``QueueListener`` and
    the dashboard board on threads. Every worker launch (and every ``pty.fork``
    used to run a tool under a pseudo-terminal) therefore trips CPython's "This
    process is multi-threaded, use of fork()/forkpty() may lead to deadlocks in
    the child" ``DeprecationWarning`` (emitted by ``os.fork``/``os.forkpty``
    since Python 3.12). The fork paths are deliberately engineered to be
    fork-safe (workers fork-then-run carefully; the pty child immediately
    ``execvp``s), so silence that warning at the point of the fork rather than
    leaking it onto downstream users' consoles or forcing them to configure a
    global filter.

    Only the fork-with-threads warning is suppressed; any other warning raised
    while forking still propagates.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".* is multi-threaded, use of fork(pty)?\(\) may lead to deadlocks "
                    r"in the child",
            category=DeprecationWarning)
        yield


class FileLockTimeout(TimeoutError):
    """
    A :class:`FileLock` was not had in time.

    Its own class so that a caller can tell it apart from a :class:`TimeoutError`
    raised by the work it was guarding.

    Attributes:
        path (str): The file the lock guards.
        timeout (float): How long it was waited for; None if without a limit.
        fallback (str): The fallback marker that was in the way, where the
            filesystem cannot lock files (see :class:`FileLock`); None otherwise.
    """

    def __init__(self, path: str, timeout: Optional[float], holder: str,
                 fallback: Optional[str] = None):
        # FileLock.acquire() passes its own timeout through, which may be None.
        # A wait without a limit only ends once the lock is held, so it never
        # raises today, but the message must not depend on that.
        waited = "" if timeout is None else f" after {timeout}s"
        super().__init__(f"Timed out{waited} waiting for the lock on {path}: {holder}")
        self.path = path
        self.timeout = timeout
        self.fallback = fallback


class FileLock:
    """
    A lock on a file, held by one thread of one process at a time.

    The lock is kept beside the file it guards, which need not exist: a lock
    file, ``<path>.lock``, and a fallback marker, ``<path>.sc_lock`` (see
    below). Callers name the file they are locking; only this class names the
    files that lock it. The path is resolved first, so a symlink is followed:
    every spelling of one file shares its lock, and the lock's files sit beside
    the file itself, not beside the link.

    ``fasteners`` locks with ``fcntl.lockf`` on POSIX, which is held per
    *process*: a second thread acquiring the same lock succeeds at once, and the
    first release through any descriptor on the file drops it for the whole
    process. On its own it cannot tell this process's threads apart, so two
    pieces of code each taking a lock on one file -- two threads, or a resolver
    and the cache sweep -- walk straight into one another, and on Windows, where
    ``msvcrt`` locks per handle, deadlock instead.

    This pairs it with a thread lock and a hold count, and hands every caller in
    the process the same instance for a given file (see :func:`get_file_lock`).
    Threads queue on the thread lock, and only the outermost acquire and release
    touch the file lock. It is re-entrant: the thread holding it can take it
    again, and the file lock is released with the last hold.

    Where the filesystem cannot lock files at all -- an NFS mount without lock
    support is the usual case -- the lock is held instead by creating a marker
    beside it (:attr:`fallback_path`) and released by deleting it. A process
    that is killed while holding it leaves the marker behind, and nothing
    breaks it automatically: whoever next waits for the lock times out with an
    error naming the marker, to be deleted once no process is using it.

    A ``fork`` child starts with no instance held; see :func:`get_file_lock`.
    One forked by the holding thread inherits that thread's hold, and can still
    release it on its way out of the block, but the file lock and the marker
    stay the parent's: the release leaves them alone.
    """

    def __init__(self, path: Union[str, "os.PathLike"]):
        # Absolute and with every symlink resolved, so that one file has one
        # lock, named the same in every process, however it was spelled.
        self.__path = os.path.realpath(path)
        self.__lock_path = self.__path + ".lock"
        self.__fallback = self.__path + ".sc_lock"
        self.__thread_lock = threading.RLock()
        self.__file_lock = InterProcessLock(self.__lock_path)
        self.__depth = 0
        # The thread holding it, so release() can refuse every other caller,
        # and the process, so a forked child's release leaves the parent's
        # file lock and marker alone
        self.__owner: Optional[int] = None
        self.__pid: Optional[int] = None
        self.__holding_fallback = False

    @property
    def path(self) -> str:
        """The file the lock guards, as its real path."""
        return self.__path

    @property
    def lock_path(self) -> str:
        """The lock file: :attr:`path` with ``.lock`` added."""
        return self.__lock_path

    @property
    def fallback_path(self) -> str:
        """
        The marker that holds the lock where the filesystem cannot lock files:
        :attr:`path` with ``.sc_lock`` added.
        """
        return self.__fallback

    @property
    def paths(self) -> Tuple[str, str]:
        """Both of the files that lock :attr:`path`: the lock file, then the marker."""
        return self.__lock_path, self.__fallback

    def fallback_taken(self) -> Optional[float]:
        """
        When the fallback marker was created -- when the lock was last taken
        through it -- as a timestamp; None if there is no marker.

        A marker exists only while it is held, so an old one is residue from a
        process that was killed, or a hold that has lasted that long.

        Raises:
            OSError: if the marker exists but cannot be read.
        """
        try:
            return os.stat(self.__fallback).st_mtime
        except FileNotFoundError:
            return None

    @staticmethod
    def __remaining(deadline: Optional[float]) -> Optional[float]:
        if deadline is None:
            return None
        return max(0.0, deadline - time.monotonic())

    def acquire(self, timeout: Optional[float] = None) -> None:
        """
        Take the lock, waiting at most ``timeout`` seconds in all.

        Args:
            timeout (float): Seconds to wait, for this process's other threads
                and for other processes together; 0 tries once. If None, waits
                for as long as it takes.

        Raises:
            FileLockTimeout: if it is not had in time, saying whether another
                thread, another process, or the fallback marker holds it.
            OSError: where the lock file cannot be opened, or where the
                filesystem cannot lock it and the fallback marker cannot be
                created either.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        if not self.__thread_lock.acquire(timeout=-1 if timeout is None else timeout):
            raise FileLockTimeout(self.__path, timeout, "another thread of this process holds it")

        if self.__depth == 0:
            try:
                self.__take(timeout, deadline)
            except BaseException:
                self.__thread_lock.release()
                raise
            # Kept alive while held: the registry only holds it weakly, and a
            # collected lock closes its file, which drops the file lock.
            _held_file_locks[self.__path] = self
            self.__owner = threading.get_ident()
            self.__pid = os.getpid()

        self.__depth += 1

    def __take(self, timeout: Optional[float], deadline: Optional[float]) -> None:
        """
        Take the file lock, or the fallback marker where files cannot be locked.
        """
        try:
            held = self.__file_lock.acquire(timeout=self.__remaining(deadline))
        except RuntimeError:
            # fasteners' word for a lockf the filesystem refused. An OSError is
            # a lock file that cannot even be opened, and is raised: falling
            # back there would leave this process on the marker while every
            # process that can open the file locks it, each ignoring the other.
            self.__take_fallback(timeout, deadline)
            return
        if not held:
            raise FileLockTimeout(self.__path, timeout, "another process holds it")

    def __take_fallback(self, timeout: Optional[float], deadline: Optional[float]) -> None:
        """
        Hold the lock by creating :attr:`fallback_path`, which must not exist.
        """
        delay = 0.01
        while True:
            try:
                # O_EXCL, so of two processes racing for it only one creates it;
                # owner-only, so it is never wider than a lock taken with a mode.
                # It is empty, and nothing needs to open it: checking it is a
                # stat, and deleting it rests on the directory's permissions.
                os.close(os.open(self.__fallback, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
                self.__holding_fallback = True
                return
            except FileExistsError:
                pass

            remaining = self.__remaining(deadline)
            if remaining == 0.0:
                raise FileLockTimeout(
                    self.__path, timeout,
                    f"{self.__fallback} exists. This filesystem cannot lock files, so a "
                    "held lock is marked by that file instead; delete it if no process "
                    "is using it",
                    fallback=self.__fallback)
            time.sleep(delay if remaining is None else min(delay, remaining))
            delay = min(delay + 0.01, 0.1)

    def release(self) -> None:
        """
        Release one hold, and the file lock with the last.

        Raises:
            RuntimeError: if the calling thread does not hold it. Nothing is
                changed: every caller in the process shares this instance, so a
                release that went ahead would drop the file lock from under the
                thread that does hold it.
        """
        if self.__depth <= 0 or self.__owner != threading.get_ident():
            raise RuntimeError(f"The lock on {self.__path} is not held by this thread")

        self.__depth -= 1
        try:
            if self.__depth == 0:
                inherited = self.__pid != os.getpid()
                self.__owner = None
                self.__pid = None
                if _held_file_locks.get(self.__path) is self:
                    del _held_file_locks[self.__path]
                if self.__holding_fallback:
                    self.__holding_fallback = False
                    # A child forked inside the hold inherits it, but not the
                    # marker, which its parent still holds
                    if not inherited:
                        with contextlib.suppress(FileNotFoundError):
                            os.unlink(self.__fallback)
                else:
                    # Harmless in such a child: fcntl locks are not inherited,
                    # so its unlock releases nothing of the parent's
                    self.__file_lock.release()
        finally:
            self.__thread_lock.release()

    @contextlib.contextmanager
    def locked(self, timeout: Optional[float] = None) -> Iterator[None]:
        """
        Hold the lock for the length of the block.

        Args:
            timeout (float): Seconds to wait for it, in all; if None, for as
                long as it takes.

        Raises:
            FileLockTimeout: if it is not had in time; see :meth:`acquire`.
        """
        self.acquire(timeout)
        try:
            yield
        finally:
            self.release()


#: The lock on each file in use, keyed by the file's real path (FileLock.path).
#: Weak-valued, so an entry
#: lives as long as it is held or referenced, and a fresh one stands in once it
#: is neither.
_file_locks: "weakref.WeakValueDictionary[str, FileLock]" = weakref.WeakValueDictionary()
_file_locks_guard = threading.Lock()
#: Every held lock, keyed like _file_locks: what keeps a held lock alive when
#: its holder kept no reference to it.
_held_file_locks: "dict[str, FileLock]" = {}


def get_file_lock(path: Union[str, "os.PathLike"]) -> FileLock:
    """
    Returns the lock on the file ``path``, shared by every caller in the process.

    Name the file to be locked, not a lock file: the lock keeps its own files
    beside it (see :class:`FileLock`), and ``path`` itself need not exist.

    There is no need to keep it: it is the same object for as long as anyone
    holds it or has it, and is dropped once nobody does.

    A ``fork`` child gets a fresh set. The parent still holds whatever it held,
    so a child that wants a lock waits for the parent like any other process,
    and one forked while holding a lock does not hold it in the child.

    Args:
        path (str or path-like): The file to lock. A symlink is followed.
    """
    path = os.path.realpath(path)
    with _file_locks_guard:
        lock = _file_locks.get(path)
        if lock is None:
            lock = FileLock(path)
            _file_locks[path] = lock
        return lock


def _reset_file_locks_after_fork() -> None:
    """
    Drops every file lock in a freshly forked child; see :func:`get_file_lock`.

    A lock held by a thread that does not exist in the child is never released,
    and the file lock under it belongs to the parent anyway.
    """
    global _file_locks, _file_locks_guard, _held_file_locks
    _file_locks_guard = threading.Lock()
    _file_locks = weakref.WeakValueDictionary()
    _held_file_locks = {}


if hasattr(os, "register_at_fork"):  # absent on Windows, which has no fork
    os.register_at_fork(after_in_child=_reset_file_locks_after_fork)


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

        The instance is registered only once ``_init_singleton`` has finished.
        The outer ``has_cls`` check deliberately skips the lock, so publishing
        any earlier would hand a half-built instance to a second thread while
        the first is still inside ``_init_singleton`` -- which, for
        :class:`MPManager`, spends that time launching a manager process, a
        wide window in which every attribute is still missing.
        """
        if not _ManagerSingleton.has_cls(cls):
            with _ManagerSingleton._lock:
                if cls not in _ManagerSingleton._instances:
                    instance = super(_ManagerSingleton, cls).__call__(*args, **kwargs)
                    # Custom initializer for the singleton instance
                    instance._init_singleton()
                    _ManagerSingleton._instances[cls] = instance
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
        from multiprocessing.managers import SyncManager

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

        # Settings. Imported here rather than at module scope: the settings
        # module takes its file lock from this one.
        from siliconcompiler.utils.settings import SettingsManager
        self.__settings = SettingsManager(
            default_sc_path("settings.json"), self.__logger,
            system_filepath=default_sc_system_path())
        self.__transient_settings = SettingsManager(None, self.__logger)

        # Cache of paths that data sources have resolved to. Imported here rather
        # than at module scope: siliconcompiler.package imports this module, so a
        # top-level import would close a cycle.
        from siliconcompiler.package.cache import PathCache
        self.__path_cache = PathCache()

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

        from multiprocessing.managers import RemoteError

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
                except OSError:
                    # The log may already be gone, or still be held open by
                    # another handler on Windows. Leaving it behind is harmless.
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
    def get_manager() -> "SyncManager":
        """
        Provides access to the shared multiprocessing.Manager instance.

        Returns:
            multiprocessing.Manager: The singleton manager instance.
        """
        return MPManager().__manager

    @staticmethod
    def get_settings() -> "SettingsManager":
        """
        Provides access to the shared SettingsManager instance.

        Returns:
            SettingsManager: The singleton settings instance.
        """
        return MPManager().__settings

    @staticmethod
    def get_transient_settings() -> "SettingsManager":
        """
        Provides access to the shared transient SettingsManager instance.

        Returns:
            SettingsManager: The singleton transient settings instance.
        """
        return MPManager().__transient_settings

    @staticmethod
    def get_path_cache() -> "PathCache":
        """
        Provides access to the shared cache of resolved data source paths.

        There is one cache per process. Entries are keyed by a content hash of a
        data source's URI and reference, so a single cache serves every project,
        library and design in the process without them colliding.

        Returns:
            PathCache: The singleton path cache instance.
        """
        return MPManager().__path_cache

    @staticmethod
    def get_dashboard() -> "Board":
        """
        Lazily initializes and returns the singleton dashboard Board instance.

        This method ensures that the Board is only created when first requested
        and that its initialization is thread-safe.

        Returns:
            Board: The singleton dashboard Board instance.
        """
        manager = MPManager()
        if not manager.__board:
            # Imported here rather than at module scope: the board drags in the
            # whole rich/requests/PIL reporting stack, which no import of
            # siliconcompiler should have to pay for.
            from siliconcompiler.report.dashboard.cli.board import Board

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
    def __init__(self, queue):
        super().__init__(queue)

        # Bound once here rather than imported at module scope: the queue this
        # handler wraps is always a SyncManager proxy, so multiprocessing's
        # manager machinery -- one of the costlier imports in the tree -- is
        # already loaded by the time a handler exists.
        from multiprocessing.managers import RemoteError

        self._remote_error = RemoteError

    def enqueue(self, record):
        try:
            super().enqueue(record)
        except (BrokenPipeError, EOFError, ConnectionResetError, OSError,
                self._remote_error):
            # The queue is no longer reachable so fail silently. This is
            # most likely happening during shutdown, when the parent's
            # SyncManager has gone away before the child finished logging.
            pass
