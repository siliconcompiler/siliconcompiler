import atexit
import contextlib
import functools
import json
import logging
import socket
import sys
import tempfile
import threading
import time
import warnings
import weakref

import os.path

from collections import OrderedDict
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, \
    Type, Union, TYPE_CHECKING

from datetime import datetime
from fasteners import InterProcessLock
from logging.handlers import QueueHandler

from siliconcompiler.utils import default_settings_file, default_manager_dir, \
    default_sc_system_path


if TYPE_CHECKING:
    from multiprocessing.context import BaseContext
    from multiprocessing.managers import SyncManager

    from siliconcompiler.package.cache import PathCache
    from siliconcompiler.report.dashboard.cli.board import Board
    from siliconcompiler.utils.settings import SettingsManager


class SharedGroup:
    """A named rendezvous shared by every SiliconCompiler process on a manager.

    One instance lives inside the :class:`SyncManager` server process; every
    process that shares that manager reaches it by proxy. It exists so peer
    processes -- N concurrent ``Project.run()`` calls, one per point of a
    parameter sweep -- can agree on which of them drives a process-wide
    resource, and feed that one process the state it needs to drive it.

    Nothing here knows what the resource is. A group provides four things:

    * **Owner arbitration.** Exactly one member holds the group at a time,
      taken with :meth:`claim` and given back with :meth:`release`. An owner
      that stops heartbeating loses it after :attr:`OWNER_TIMEOUT`, so a member
      that dies mid-run does not take the group down with it.
    * **Member liveness.** :meth:`publish` records a heartbeat, and
      :meth:`collect` reports which members have gone silent.
    * **Keyed state.** Members publish whole snapshots under their own keys,
      last write wins; the owner collects only what changed since it last
      looked.
    * **A bounded stream.** Members append; the owner drains in order.

    The dashboard is the first user: the owner paints the terminal while every
    other run publishes its node status and log lines. The scheduler is the
    intended second -- one process arbitrating a machine-wide core budget while
    the others report what they are running -- which is why the vocabulary here
    is deliberately about members and state rather than jobs and logs.

    All state is guarded by a plain :class:`threading.Lock`: the manager server
    dispatches each proxied call on its own thread, but they are all threads of
    one process.
    """

    #: Seconds without a heartbeat after which the owner is presumed gone and
    #: the group may be claimed by another member. Generous relative to the
    #: sub-second collect cadence, because an owner stalled on slow work must
    #: not be displaced by an eager peer.
    OWNER_TIMEOUT: float = 10.0

    #: Seconds without a publish after which a member is presumed gone.
    #: Members heartbeat every dwell even with nothing to say, so at the
    #: default 0.2 s dwell this is ~150 missed ticks.
    MEMBER_TIMEOUT: float = 30.0

    #: Caps on retained state. A group can run with no owner ever attached
    #: (nothing in the group can drive the resource), so the buffers must be
    #: bounded or they would grow for the life of the manager.
    MAX_STREAM: int = 2000
    MAX_KEYS: int = 64

    def __init__(self, name: str = "") -> None:
        self.__name = name
        self.__lock = threading.Lock()

        self.__owner: Optional[Any] = None
        self.__owner_seen: float = 0.0

        # key -> (publishing member, value). Ordered so the eviction in
        # __trim can drop the oldest entry.
        self.__state: "OrderedDict[str, Tuple[Any, Any]]" = OrderedDict()
        # keys updated since the owner last collected.
        self.__dirty: Set[str] = set()
        # member -> last publish time.
        self.__seen: Dict[Any, float] = {}

        self.__stream: List[Any] = []

    def name(self) -> str:
        """Returns the name this group was registered under."""
        return self.__name

    # ------------------------------------------------------------------
    # Owner arbitration
    # ------------------------------------------------------------------
    def claim(self, member: Any) -> bool:
        """
        Try to take ownership of the group for ``member``.

        Succeeds when the group is free, already held by ``member``, or held by
        one that has not heartbeated within :attr:`OWNER_TIMEOUT`.

        Args:
            member: Identifier for the claiming process, usually its pid.

        Returns:
            bool: True if ``member`` now owns the group.
        """
        now = time.time()
        with self.__lock:
            if self.__owner is None or self.__owner == member or \
                    (now - self.__owner_seen) > self.OWNER_TIMEOUT:
                self.__owner = member
                self.__owner_seen = now
                return True
            return False

    def release(self, member: Any) -> None:
        """
        Give up ownership, if ``member`` holds it.

        Called when a member is done so the next one can take over immediately
        rather than waiting out :attr:`OWNER_TIMEOUT`.
        """
        with self.__lock:
            if self.__owner == member:
                self.__owner = None
                self.__owner_seen = 0.0

    def owner(self) -> Optional[Any]:
        """
        Returns:
            The live owner, or None if the group is unowned.
        """
        with self.__lock:
            return self.__live_owner(time.time())

    # ------------------------------------------------------------------
    # Member side
    # ------------------------------------------------------------------
    def publish(self, member: Any, state: Dict[str, Any], stream: List[Any]) -> bool:
        """
        Hand this member's state and stream entries to the owner.

        Also records ``member``'s heartbeat, so a member with nothing new must
        still call this (with empty arguments) to stay live.

        Args:
            member: Identifier for the publishing process, usually its pid.
            state (dict): Whole snapshots keyed by member-chosen ids -- not
                deltas. Last write wins, which keeps merge logic out of the
                group entirely.
            stream (list): Entries to append to the shared stream, in order.

        Returns:
            bool: True if an owner is currently live. A member uses this to
            notice the owner went away so it can take over.
        """
        now = time.time()
        with self.__lock:
            self.__seen[member] = now

            for key, value in (state or {}).items():
                if key not in self.__state:
                    self.__trim()
                self.__state[key] = (member, value)
                self.__dirty.add(key)

            if stream:
                self.__stream.extend(stream)
                overflow = len(self.__stream) - self.MAX_STREAM
                if overflow > 0:
                    del self.__stream[:overflow]

            return self.__live_owner(now) is not None

    # ------------------------------------------------------------------
    # Owner side
    # ------------------------------------------------------------------
    def collect(self, member: Any) -> Optional[Tuple[Dict[str, Any], List[Any], List[str]]]:
        """
        Take everything published since the last call and heartbeat the owner.

        Args:
            member: Identifier for the process claiming to be the owner.

        Returns:
            tuple or None: ``(state, stream, orphaned)`` where ``state`` maps
            keys to the latest value published by *another* member, ``stream``
            is the accumulated entries in order, and ``orphaned`` lists the keys
            whose publisher has gone silent. Returns None if ``member`` is not
            (or is no longer) the owner, which tells the caller to step down.
        """
        now = time.time()
        with self.__lock:
            if self.__owner != member:
                return None
            self.__owner_seen = now

            state: Dict[str, Any] = {}
            for key in self.__dirty:
                entry = self.__state.get(key)
                if entry is None:
                    continue
                publisher, value = entry
                if publisher == member:
                    # The owner's own state never travels through the group;
                    # this can only be a leftover from a previous owner.
                    continue
                state[key] = value
            self.__dirty.clear()

            stream, self.__stream = self.__stream, []

            return state, stream, self.__expire(now, member)

    # ------------------------------------------------------------------
    # Internal helpers -- all called with the lock held.
    # ------------------------------------------------------------------
    def __live_owner(self, now: float) -> Optional[Any]:
        if self.__owner is None:
            return None
        if (now - self.__owner_seen) > self.OWNER_TIMEOUT:
            return None
        return self.__owner

    def __expire(self, now: float, owner: Any) -> List[str]:
        """Drop members that have gone silent and report their keys."""
        departed = set(
            member for member, seen in self.__seen.items()
            if member != owner and (now - seen) > self.MEMBER_TIMEOUT)
        if not departed:
            return []

        for member in departed:
            del self.__seen[member]

        # The values themselves are kept: what a departed member last said is
        # usually still worth showing. Only its liveness is reported, so the
        # owner can stop treating it as in flight. A member that comes back
        # simply publishes again and is live again.
        return [key for key, (member, _) in self.__state.items() if member in departed]

    def __trim(self) -> None:
        """Evict the oldest key once :attr:`MAX_KEYS` distinct keys are held."""
        while len(self.__state) >= self.MAX_KEYS:
            key, _ = self.__state.popitem(last=False)
            self.__dirty.discard(key)


# Groups live in the manager's server process, one per name, so a caller asks
# for "dashboard" and gets the same object every other process asked for. The
# server keys its object table on id(obj), so returning the same instance for a
# name also means every process shares one entry rather than accumulating one
# per connection.
_SHARED_GROUPS: Dict[str, SharedGroup] = {}
_SHARED_GROUPS_LOCK = threading.Lock()


def get_shared_group(name: str) -> SharedGroup:
    """
    Returns the manager server's :class:`SharedGroup` for ``name``.

    Registered as a ``SCSyncManager`` typeid; do not call this directly from a
    client process (it would build a second, purely local group). Use
    :meth:`MPManager.get_shared_group` instead.
    """
    group = _SHARED_GROUPS.get(name)
    if group is None:
        with _SHARED_GROUPS_LOCK:
            group = _SHARED_GROUPS.get(name)
            if group is None:
                group = SharedGroup(name)
                _SHARED_GROUPS[name] = group
    return group


def _process_created(pid: int) -> Optional[float]:
    """When process ``pid`` started, so a reused pid is not mistaken for it."""
    import psutil

    try:
        return psutil.Process(pid).create_time()
    except psutil.Error:
        return None


def _process_alive(pid: int, created: Optional[float]) -> bool:
    """Is ``pid`` still the process that was running when ``created`` was taken?"""
    import psutil

    try:
        process = psutil.Process(pid)
        if created is not None and process.create_time() != created:
            return False
        return process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False
    except psutil.Error:
        # Not ours to inspect is not the same as gone.
        return True


class _ManagerClients:
    """The processes using one manager server, kept inside that server.

    The server is started by whichever process first needed it, but others
    join it: those handed its address, those that found it in the environment
    (see ``MANAGER_ENVIRONMENT``), and those that found it through their
    terminal (see ``_terminal_rendezvous``). Its groups hold state they
    all rely on -- the dashboard is the reason it matters -- so the server must
    outlive the process that happened to start it. It stays up while any
    process is attached, and stops itself once the last has detached or died.

    Each :class:`MPManager` attaches under a token of its own rather than under
    its pid: one process can hold several in turn, and the detach of one must
    not drop another still attached. The pid is kept to notice a process that
    died without detaching.

    Once the last client is gone the server is closing, and that is final:
    an attach after that point fails, so a process arriving as the server
    stops starts one of its own rather than joining one about to vanish.
    """

    #: Seconds between sweeps for clients that died without detaching.
    POLL: float = 1.0

    def __init__(self) -> None:
        self.__lock = threading.Lock()
        # token -> (pid, when that pid started)
        self.__clients: Dict[str, Tuple[int, Optional[float]]] = {}
        # Nothing is attached while the server starts up, which must not read
        # as everyone having left.
        self.__attached = False
        self.__closing = False

    def attach(self, token: str, pid: int) -> bool:
        """
        Register a client.

        Returns:
            bool: False if the server is already closing; join another.
        """
        with self.__lock:
            if self.__closing:
                return False
            self.__clients[token] = (pid, _process_created(pid))
            self.__attached = True
            return True

    def detach(self, token: str) -> int:
        """
        Unregister a client.

        Returns:
            int: How many clients remain. At zero the server is closing, and
            the caller may shut it down rather than wait for it to stop itself.
        """
        with self.__lock:
            self.__clients.pop(token, None)
            return self.__sweep()

    def sweep(self) -> bool:
        """
        Drop clients that died without detaching.

        Returns:
            bool: True once the server is closing.
        """
        with self.__lock:
            self.__sweep()
            return self.__closing

    def __sweep(self) -> int:
        """Called with the lock held."""
        for token, (pid, created) in list(self.__clients.items()):
            if not _process_alive(pid, created):
                del self.__clients[token]
        if self.__attached and not self.__clients:
            self.__closing = True
        return len(self.__clients)


# One per server process, for the same reason as _SHARED_GROUPS.
_MANAGER_CLIENTS = _ManagerClients()


def get_manager_clients() -> _ManagerClients:
    """
    Returns the manager server's :class:`_ManagerClients`.

    Registered as a ``SCSyncManager`` typeid, like :func:`get_shared_group`.
    """
    return _MANAGER_CLIENTS


def _watch_manager_clients() -> None:
    """Stops the server once its clients are all gone. Runs in the server."""
    import multiprocessing

    while not _MANAGER_CLIENTS.sweep():
        time.sleep(_ManagerClients.POLL)

    # Set by Server.serve_forever(), whose loop exits once its stop_event is
    # set -- the same thing a client's shutdown() does.
    server = getattr(multiprocessing.current_process(), "_manager_server", None)
    if server is not None:
        server.stop_event.set()


def _init_manager_server() -> None:
    """Prepares the manager's server process, before it starts serving."""
    import multiprocessing

    # Listen from a temporary directory of the server's own. One inherited from
    # the process that started it is removed when that process exits, and the
    # socket in it with it, while other clients may still need to connect.
    multiprocessing.current_process()._config.pop("tempdir", None)

    threading.Thread(target=_watch_manager_clients, name="sc-manager-clients",
                     daemon=True).start()


# The registered callable runs inside the manager's server process, so every
# process sharing the manager -- the one that started it and anyone that
# connects to its address -- gets a proxy to the *same* group. That is what
# lets N concurrent runs share one dashboard. Registered on the manager class
# so the typeid exists before either start() or connect().
@functools.lru_cache(maxsize=None)
def _sync_manager_class() -> "Type[SyncManager]":
    """Returns :class:`SyncManager` extended with SiliconCompiler's shared types.

    Subclassed rather than registering onto ``SyncManager`` itself so the extra
    typeids do not leak into unrelated managers created by user code.
    Registration is class level and must be identical on both ends: the server
    process builds the object, and every client that connects builds a proxy
    for it, so both sides construct this same class.

    Built on first use, not at import, so ``multiprocessing.managers`` stays out
    of module import time.
    """
    from multiprocessing.managers import SyncManager

    class SCSyncManager(SyncManager):
        pass

    SCSyncManager.register("shared_group", callable=get_shared_group)
    SCSyncManager.register("manager_clients", callable=get_manager_clients)
    return SCSyncManager


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


#: Where the process that starts a manager server leaves its address, so that
#: every SiliconCompiler process it launches -- by fork, spawn or subprocess,
#: handed a Project or not -- joins that server rather than starting its own.
#: Joining is what puts concurrent runs on one dashboard. The value also names
#: the host and the SiliconCompiler and Python versions, so an address that
#: travelled somewhere it cannot work (a cluster node, another install) is
#: ignored rather than tried.
MANAGER_ENVIRONMENT = "SC_MANAGER"


def _terminal_rendezvous() -> Optional[str]:
    """
    Returns the file through which unrelated runs printing to this terminal
    find one manager, and so draw one dashboard; None if standard output is not
    a terminal, where there is no dashboard to share.

    Kept under the user's own SiliconCompiler directory, never somewhere shared:
    a client trusts the server a rendezvous names. Named for the host as well as
    the terminal, since that directory may be one home shared across machines.
    """
    try:
        terminal = os.ttyname(1)
    except (AttributeError, OSError):
        # Not a terminal, or Windows, which has no ttyname()
        return None

    terminal = terminal.removeprefix("/dev/").replace(os.sep, "-")
    return os.path.join(default_manager_dir(), f"{socket.gethostname()}-{terminal}.json")


class MPManager(metaclass=_ManagerSingleton):
    """
    A singleton manager for handling multiprocessing resources in SiliconCompiler.

    This class provides centralized, thread-safe access to shared resources
    like a logger, a multiprocessing.Manager, and a dashboard Board instance.
    It is designed to be instantiated once and accessed globally.
    """
    __ENABLE_LOGGER: bool = True
    #: Seconds to wait for the terminal's rendezvous before acting alone. Held
    #: only while one process looks for a server or starts one.
    __RENDEZVOUS_TIMEOUT: float = 10.0
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
        SCSyncManager = _sync_manager_class()

        self.__start = datetime.now()
        self.__error = False

        # Parent logger setup
        now_file = self.__start.strftime("%Y-%m-%d-%H-%M-%S-%f")
        self.__logfile = os.path.join(tempfile.gettempdir(),
                                      "siliconcompiler",
                                      f"{now_file}_{id(self)}.log")
        self._init_logger()

        # Manager to handle shared data between processes. Join the one this
        # process was handed, else the one its environment names, else the one
        # its terminal's other runs use, else start one. Whichever it is, this
        # process attaches to it, which is what keeps a server up for as long
        # as anyone still uses it.
        self.__pid = os.getpid()
        self.__token = f"{self.__pid}-{os.urandom(8).hex()}"
        self.__manager_server = False
        self.__environment = None
        self.__rendezvous = None

        manager = None
        address = MPManager._get_manager_address()
        if address is not None:
            manager = self.__join(SCSyncManager, address, hint=False)
        if manager is None:
            address = MPManager._address_from_environment()
            if address is not None:
                manager = self.__join(SCSyncManager, address, hint=True)
        if manager is None:
            manager = self.__join_terminal(SCSyncManager)

        self.__manager = manager

        # Dashboard singleton setup
        self.__board_lock = self.__manager.Lock()
        self.__board = None

        # Proxies to the manager server's SharedGroups, keyed by name, plus
        # the pid they were built in. A proxy must never be used from a process
        # other than the one that created it: under ``fork`` a child inherits
        # the live socket, and driving it from both ends corrupts the manager's
        # framed protocol. Keying on the pid makes inherited proxies inert --
        # the child transparently builds its own on first use. A plain
        # threading.Lock guards this (it is per-process state; a manager Lock
        # would mean a proxy round trip just to read a cached proxy).
        self.__groups: Dict[str, Optional[SharedGroup]] = {}
        self.__group_pid = None
        self.__group_lock = threading.Lock()

        # Settings. Imported here rather than at module scope: the settings
        # module takes its file lock from this one.
        from siliconcompiler.utils.settings import SettingsManager
        self.__settings = SettingsManager(
            default_settings_file(), self.__logger,
            system_filepath=default_sc_system_path())
        self.__transient_settings = SettingsManager(None, self.__logger)

        # Cache of paths that data sources have resolved to. Imported here rather
        # than at module scope: siliconcompiler.package imports this module, so a
        # top-level import would close a cycle.
        from siliconcompiler.package.cache import PathCache
        self.__path_cache = PathCache()

        # Register cleanup function to run at exit
        atexit.register(MPManager.stop)

        # And from multiprocessing's own exit path, which is how a pool worker
        # leaves -- often the very process drawing a sweep's dashboard. Python
        # 3.12, for one, exits a fork or forkserver child without running
        # atexit at all, and where atexit does run it comes after multiprocessing
        # has dropped this process's proxies and shut down a manager it started,
        # leaving the terminal in the dashboard's screen and other processes
        # without their server. The priority puts it ahead of both of those.
        from multiprocessing import util
        self.__exit_hook = util.Finalize(None, MPManager.stop, exitpriority=100)

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
        stops the dashboard service, detaches from the multiprocessing manager,
        and finally removes the singleton instance from the registry.

        The process that started the manager shuts it down only if nobody else
        is still attached. Otherwise it leaves the server running for them, and
        the server stops itself once the last has gone.
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
                except OSError:
                    # The log may already be gone, or still be held open by
                    # another handler on Windows. Leaving it behind is harmless.
                    pass

            # Stop the dashboard service if it's running
            if manager.__board:
                try:
                    with manager.__board_lock:
                        if manager.__board:
                            manager.__board.stop(force=True, dump_log=False)
                            manager.__board = None
                except Exception:
                    # Try without the lock, which lives in the manager's server:
                    # giving the terminal back must not depend on reaching it.
                    if manager.__board:
                        manager.__board.stop(force=True, dump_log=False)
                        manager.__board = None

            # A forked child inherits this instance, but the attachment and the
            # server are its parent's, and the parent is still using them.
            if manager.__pid == os.getpid():
                remaining = manager.__detach()

                if manager.__manager_server:
                    MPManager.__address = None
                    if os.environ.get(MANAGER_ENVIRONMENT) == manager.__environment:
                        del os.environ[MANAGER_ENVIRONMENT]

                    if remaining:
                        manager.__leave_server_running()
                    else:
                        # Shut down the multiprocessing manager
                        manager.__forget_terminal()
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
                manager.__exit_hook.cancel()
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
    def get_shared_group(name: str) -> Optional[SharedGroup]:
        """
        Returns a proxy to the manager server's :class:`SharedGroup` ``name``.

        A group is how peer SiliconCompiler processes agree on which of them
        drives a process-wide resource, and feed that one process what it needs
        to drive it -- see :class:`SharedGroup`.

        The proxy is cached per name *and* per process, and rebuilt after a
        fork, so an inherited copy is never reused across a process boundary:
        under ``fork`` a child inherits the live socket, and driving it from
        both ends corrupts the manager's framed protocol.

        Args:
            name (str): The group to join, e.g. ``"dashboard"``.

        Returns:
            SharedGroup proxy, or None if the manager cannot provide one -- in
            which case callers must degrade to acting alone in this process
            rather than failing.
        """
        manager = MPManager()

        pid = os.getpid()
        with manager.__group_lock:
            if manager.__group_pid != pid:
                # This process inherited the parent's proxies across a fork.
                # Drop them; each is rebuilt below with its own connection.
                manager.__groups = {}
                manager.__group_pid = pid

            if name in manager.__groups:
                return manager.__groups[name]

            group = None
            try:
                group = manager.__manager.shared_group(name)
            except Exception as e:
                # An older manager server (no such typeid), a shut-down
                # manager, or a broken connection. Callers degrade to acting
                # alone rather than failing the run.
                manager.__logger.debug(f"Shared group '{name}' unavailable: {e}")
            manager.__groups[name] = group
            return group

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

    @staticmethod
    def __compatibility() -> List[str]:
        """What a process must share with a server to join it by environment."""
        from siliconcompiler._metadata import detailed_version

        return [socket.gethostname(), str(detailed_version),
                f"{sys.version_info.major}.{sys.version_info.minor}"]

    @staticmethod
    def __environment_value(address) -> str:
        """The value of ``MANAGER_ENVIRONMENT`` naming the server at ``address``."""
        return json.dumps({"address": address, "compatibility": MPManager.__compatibility()})

    @staticmethod
    def _address_from_environment():
        """
        The address in ``MANAGER_ENVIRONMENT``, if there is one this process
        can use.

        Returns:
            The address, or None if the variable is unset, unreadable, or names
            a server on another host or of another SiliconCompiler or Python
            version.
        """
        return MPManager.__address_from_value(os.environ.get(MANAGER_ENVIRONMENT))

    @staticmethod
    def __address_from_value(value: Optional[str]):
        """Reads a value written by :meth:`__environment_value`; see above."""
        if not value:
            return None

        try:
            entry = json.loads(value)
            if entry["compatibility"] != MPManager.__compatibility():
                return None
            address = entry["address"]
        except (ValueError, KeyError, TypeError):
            return None

        # JSON has no tuples, and a TCP address is one.
        return tuple(address) if isinstance(address, list) else address

    def __join(self, manager_class: "Type[SyncManager]", address, hint: bool) \
            -> Optional["SyncManager"]:
        """
        Connect to the server at ``address`` and attach to it.

        Args:
            manager_class: The manager class to connect with.
            address: Where the server listens.
            hint (bool): Whether the address was found rather than handed over.
                Naming a server that has since stopped is the ordinary way for
                a found one to miss, so that is not worth a warning; a handed
                one ought to have worked.

        Returns:
            The connected manager, or None if the server cannot be joined.
        """
        from multiprocessing import AuthenticationError

        manager = manager_class(address=address, authkey=MPManager.__authkey)
        try:
            manager.connect()
            if self.__attach(manager):
                MPManager._set_manager_address(address)
                return manager
            reason = "it is shutting down"
        except (OSError, EOFError, AuthenticationError) as e:
            reason = str(e)

        log = self.__logger.debug if hint else self.__logger.warning
        log(f"Manager at {address} unavailable ({reason}); falling back to server mode")
        return None

    def __serve(self, manager_class: "Type[SyncManager]") -> "SyncManager":
        """Start a server, attach to it, and name it in the environment."""
        # Pin the start method for the manager's server process: its
        # start() launches a process, and under the Python 3.14 default
        # (forkserver) that re-imports __main__ and breaks unguarded
        # module-level proj.run() scripts. See get_process_context().
        manager = manager_class(authkey=MPManager.__authkey, ctx=get_process_context())
        with forking():
            manager.start(initializer=_init_manager_server)
        # Replaces an address that could not be reached, so that what
        # Project pickles for its workers is this server, not that one.
        MPManager.__address = manager.address
        self.__manager_server = True
        self.__attach(manager)

        self.__environment = MPManager.__environment_value(manager.address)
        os.environ[MANAGER_ENVIRONMENT] = self.__environment
        return manager

    def __join_terminal(self, manager_class: "Type[SyncManager]") -> "SyncManager":
        """
        Join the server the other runs printing to this terminal use, or start
        it for them.

        Runs that share a terminal share its dashboard, but they need not be
        related: the workers of a pool whose parent never started a manager are
        siblings, and nothing reaches one from another through inheritance.
        They meet at :func:`_terminal_rendezvous` instead, which the first to
        arrive fills in and the rest join. The check and the start happen under
        the file's lock, so N workers arriving at once start one server, not N.

        Anywhere the file cannot be used, this process starts a server of its
        own, as if there were no terminal.
        """
        path = _terminal_rendezvous()
        if path is None:
            return self.__serve(manager_class)

        lock = get_file_lock(path)
        try:
            os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
            lock.acquire(timeout=MPManager.__RENDEZVOUS_TIMEOUT)
        except (FileLockTimeout, OSError) as e:
            self.__logger.debug(f"Cannot lock {path} ({e}); not sharing a manager "
                                "with this terminal")
            return self.__serve(manager_class)

        try:
            try:
                with open(path, encoding="utf-8") as f:
                    address = MPManager.__address_from_value(f.read())
            except OSError:
                address = None

            if address is not None:
                manager = self.__join(manager_class, address, hint=True)
                if manager is not None:
                    return manager

            manager = self.__serve(manager_class)
            try:
                # Written whole, then renamed into place, so a reader that does
                # not take the lock never sees half of it.
                staging = f"{path}.{self.__token}"
                fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(self.__environment)
                os.replace(staging, path)
                self.__rendezvous = path
            except OSError as e:
                self.__logger.debug(f"Cannot write {path} ({e}); not sharing a manager "
                                    "with this terminal")
            return manager
        finally:
            lock.release()

    def __forget_terminal(self) -> None:
        """Remove this server from the terminal's rendezvous, if it is still there."""
        path = self.__rendezvous
        if path is None:
            return
        self.__rendezvous = None

        try:
            with get_file_lock(path).locked(timeout=MPManager.__RENDEZVOUS_TIMEOUT):
                with open(path, encoding="utf-8") as f:
                    ours = f.read() == self.__environment
                if ours:
                    os.remove(path)
        except (FileLockTimeout, OSError):
            # Left behind, it names a server that is gone, which the next run
            # notices and replaces.
            pass

    def __attach(self, manager: "SyncManager") -> bool:
        """
        Register this instance with the server ``manager`` is connected to.

        Returns:
            bool: False if the server is shutting down, or cannot be asked.
        """
        try:
            return bool(manager.manager_clients().attach(self.__token, self.__pid))
        except Exception:
            return False

    def __detach(self) -> int:
        """
        Unregister this instance from its server.

        Returns:
            int: How many other clients remain attached; 0 if the server
            cannot be asked, since then there is nobody it could still serve.
        """
        try:
            return int(self.__manager.manager_clients().detach(self.__token))
        except Exception:
            return 0

    def __leave_server_running(self) -> None:
        """
        Let this process exit without taking its manager server down.

        Other processes are still attached to it, their dashboard among them,
        and it stops itself once the last has gone (see ``_ManagerClients``).
        Two things would otherwise end it here: the finalizer start() registered
        to shut it down at exit, and multiprocessing's own exit handler, which
        joins every child process and so would hold this one open until the
        server's last client had finished.
        """
        import multiprocessing.process

        self.__manager.shutdown.cancel()
        multiprocessing.process._children.discard(self.__manager._process)


class SharedGroupMember:
    """This process's participation in a named :class:`SharedGroup`.

    Wraps the two things every group member has to do, so no caller has to
    write them again:

    * **Take the role, or don't.** :meth:`start` claims the group. Winning
      makes this process the owner; losing makes it a publisher.
    * **Run the matching loop.** The owner *collects* on a background thread,
      folding in what the others published. Everyone else *publishes* on one,
      shipping its own state and heartbeating so the owner knows it is alive.

    Both loops pace themselves the same way: they wake immediately on ``wake``
    (so real work is never delayed), and back off to ``idle_dwell`` after a
    stretch with nothing to say, so a lone process is not paying for a proxy
    round trip every tick to be told nothing happened.

    If the manager cannot provide the group, :meth:`start` reports this process
    as the owner and runs no loops at all -- callers degrade to acting alone
    rather than losing the feature.

    Args:
        name (str): Group to join, e.g. ``"dashboard"``.
        publish (callable): Returns ``(state, stream)`` to hand the owner --
            whole snapshots keyed by id, plus stream entries. Return empty for
            "nothing new"; the heartbeat still goes out.
        collect (callable): Called on the owner with ``(state, stream,
            orphaned)`` as they arrive. See :meth:`SharedGroup.collect`.
        on_promote (callable, optional): Called when this member takes a
            vacated group over mid-run. Return True to accept the role and end
            the publish loop, False to decline it (the role is given back).
            When omitted, a member never promotes.
        wake (threading.Event, optional): Set by the caller when there is new
            work; makes the next tick immediate.
        stop (threading.Event, optional): Set by the caller to end both loops.
        dwell (float): Tick period while there is traffic.
        idle_dwell (float): Tick period once there has not been any. Must stay
            well inside :attr:`SharedGroup.OWNER_TIMEOUT` -- the owner's
            collect call doubles as its heartbeat.
    """

    #: Ticks of silence before backing off to ``idle_dwell``.
    IDLE_TICKS: int = 25

    #: Seconds between attempts to take over a vacated group, so N orphaned
    #: members cannot hammer the manager racing for it.
    PROMOTE_INTERVAL: float = 1.0

    def __init__(self,
                 name: str,
                 publish: Callable[[], Tuple[Dict[str, Any], List[Any]]],
                 collect: Callable[[Dict[str, Any], List[Any], List[str]], None],
                 on_promote: Optional[Callable[[], bool]] = None,
                 wake: Optional[threading.Event] = None,
                 stop: Optional[threading.Event] = None,
                 dwell: float = 0.2,
                 idle_dwell: float = 1.0):
        self.__name = name
        self.__publish = publish
        self.__collect = collect
        self.__on_promote = on_promote

        self.__wake = wake if wake is not None else threading.Event()
        self.__stop = stop if stop is not None else threading.Event()

        self.__dwell = dwell
        self.__idle_dwell = idle_dwell

        self.__member = None
        self.__thread: Optional[threading.Thread] = None
        self.__is_owner = False
        self.__claimed = False
        self.__unavailable = False
        self.__last_promote = 0.0

    @property
    def is_owner(self) -> bool:
        """True while this process owns the group."""
        return self.__is_owner

    @property
    def claimed(self) -> bool:
        """True while this process holds a role it has not given back."""
        return self.__claimed

    @property
    def thread(self) -> Optional[threading.Thread]:
        """The background loop, or None if none is running."""
        return self.__thread

    def group(self) -> Optional[SharedGroup]:
        """
        Returns the group proxy, or None if it is unavailable here.

        Once a call has failed the group is not retried, so a dead manager
        cannot cost a round trip per tick for the rest of the process's life.
        """
        if self.__unavailable:
            return None

        group = MPManager.get_shared_group(self.__name)
        if group is None:
            self.__unavailable = True
        return group

    def start(self) -> bool:
        """
        Claim the group and start the loop that matches the outcome.

        Returns:
            bool: True if this process owns the group and should drive the
            resource. Also True when the group is unavailable, so a caller with
            no manager behaves exactly as it would with no group at all.
        """
        self.__member = os.getpid()

        group = self.group()
        if group is None:
            self.__is_owner = True
            return True

        try:
            self.__claimed = bool(group.claim(self.__member))
        except Exception:
            # Unreachable between the lookup and the call. Act alone rather
            # than lose the feature.
            self.__unavailable = True
            self.__is_owner = True
            return True

        self.__is_owner = self.__claimed
        self.__thread = threading.Thread(
            target=self._collect_loop if self.__is_owner else self._publish_loop,
            name=f"sc-group-{self.__name}",
            daemon=True)
        self.__thread.start()
        return self.__is_owner

    def join(self) -> None:
        """Waits for the background loop to finish."""
        thread = self.__thread
        if thread and thread is not threading.current_thread():
            thread.join()

    def release(self) -> None:
        """
        Give the role back so another process can take it immediately.

        A no-op if this member never held one, which also keeps a caller that
        was driven directly (tests, embedders) off the manager entirely.
        """
        self.__is_owner = False

        if not self.__claimed:
            return
        self.__claimed = False

        group = self.group()
        if group is None:
            return

        try:
            group.release(self.__member)
        except Exception:
            # Nothing to do: the role also lapses once the heartbeat goes
            # stale.
            self.__unavailable = True

    # ------------------------------------------------------------------
    # Loops
    # ------------------------------------------------------------------
    def _collect_loop(self) -> None:
        """Owner side: fold in what the other members published."""
        idle = 0
        dwell = self.__dwell

        while not self.__stop.wait(timeout=dwell):
            group = self.group()
            if group is None:
                return

            try:
                collected = group.collect(self.__member)
            except Exception:
                # Manager gone (shutdown, broken connection). There is nothing
                # left to collect; the caller keeps driving what it has.
                self.__unavailable = True
                return

            if collected is None:
                # Another process took the group -- only possible if this one's
                # heartbeat went stale. Step down and let it drive.
                self.__is_owner = False
                self.__claimed = False
                return

            state, stream, orphaned = collected
            self.__collect(state, stream, orphaned)

            if state or stream or orphaned:
                idle = 0
                dwell = self.__dwell
            else:
                idle += 1
                if idle >= self.IDLE_TICKS:
                    dwell = self.__idle_dwell

    def _publish_loop(self) -> None:
        """Member side: ship state to the owner, and take over if it vanishes."""
        idle = 0
        dwell = self.__dwell

        while not self.__stop.is_set():
            # The caller sets ``wake`` when there is new state, so a busy run
            # ticks immediately regardless of the timeout; the timeout only
            # paces the empty heartbeats.
            self.__wake.wait(timeout=dwell)
            self.__wake.clear()

            if self.__stop.is_set():
                break

            sent, alive = self._send()

            if sent:
                idle = 0
                dwell = self.__dwell
            else:
                idle += 1
                if idle >= self.IDLE_TICKS:
                    dwell = self.__idle_dwell

            if not alive and self._try_promote():
                # The collect loop owns this member from here on.
                return

        # Final flush, so the last state is not lost to the race between the
        # caller finishing and the owner's next collect.
        self._send()

    def _send(self) -> Tuple[bool, bool]:
        """
        One publish. Returns ``(sent anything, an owner is live)``.
        """
        group = self.group()
        if group is None:
            return False, True

        state, stream = self.__publish()

        try:
            return bool(state or stream), bool(group.publish(self.__member, state, stream))
        except Exception:
            self.__unavailable = True
            return False, True

    def _try_promote(self) -> bool:
        """
        Take a vacated group over.

        The owner's process can exit -- a pool retiring whichever worker
        happened to claim it first -- while the rest are still running. Rather
        than lose the resource for everyone, the remaining members race for it
        and one wins.
        """
        if self.__on_promote is None or self.__stop.is_set():
            return False

        now = time.time()
        if (now - self.__last_promote) < self.PROMOTE_INTERVAL:
            return False
        self.__last_promote = now

        group = self.group()
        if group is None:
            return False

        try:
            if not group.claim(self.__member):
                return False
        except Exception:
            self.__unavailable = True
            return False

        self.__claimed = True

        if not self.__on_promote():
            # Declined -- the caller is tearing down. Hand it straight back.
            self.release()
            return False

        # Swap this member from publishing to collecting. The publish loop
        # returns as soon as this does, so handing __thread over here is what
        # keeps the group's traffic flowing to the new owner.
        self.__is_owner = True
        self.__thread = threading.Thread(
            target=self._collect_loop, name=f"sc-group-{self.__name}", daemon=True)
        self.__thread.start()
        return True


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
