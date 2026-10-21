import contextlib
import gc
import json
import logging
import multiprocessing
import os
import re
import stat
import subprocess
import sys
import threading
import time
import warnings

from multiprocessing.managers import RemoteError
from unittest.mock import patch

import psutil
import pytest

from siliconcompiler.utils import default_manager_dir
from siliconcompiler.utils import multiprocessing as multiprocessing_utils
from siliconcompiler.utils.multiprocessing import MPManager, MPQueueHandler, \
    _ManagerSingleton, get_process_context, forking, get_file_lock, FileLock, \
    FileLockTimeout, SharedGroup, get_shared_group, _sync_manager_class, \
    MANAGER_ENVIRONMENT, _ManagerClients, _process_alive, _process_created, \
    _terminal_rendezvous
from siliconcompiler.report.dashboard.cli.board import Board
from siliconcompiler.utils.settings import SettingsManager


def test_get_process_context_linux(monkeypatch):
    '''On Linux the start method is fork, not the interpreter default (forkserver from 3.14),
    so unguarded module-level proj.run() scripts keep working.'''
    monkeypatch.setattr("sys.platform", "linux")
    # Patched because Windows has no fork context to return.
    with patch("multiprocessing.get_context") as get_ctx:
        get_process_context()
        get_ctx.assert_called_once_with("fork")


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_get_process_context_non_linux(monkeypatch, platform):
    '''Off Linux fork is either unavailable (Windows) or unsafe with threads
    (macOS), so we pin spawn explicitly rather than relying on the default.'''
    monkeypatch.setattr("sys.platform", platform)
    with patch("multiprocessing.get_context") as get_ctx:
        get_process_context()
        get_ctx.assert_called_once_with("spawn")


def test_init_singleton():
    man0 = MPManager()
    man1 = MPManager()

    assert man0 is man1

    assert MPManager in _ManagerSingleton._instances


def test_singleton_is_not_published_until_initialized():
    '''The outer has_cls() check skips the lock, so publishing the instance
    before _init_singleton() finishes hands a half-built object to any other
    thread that asks for it meanwhile -- and _init_singleton() spends that
    window launching a manager process.'''
    # Guard against the test going vacuous: once the manager exists, every thread
    # takes the fast path and _init_singleton() is never raced at all.
    MPManager.stop()
    assert not _ManagerSingleton.has_cls(MPManager)

    errors = []
    instances = []
    barrier = threading.Barrier(8)

    def race():
        barrier.wait()
        try:
            manager = MPManager()
            # Touch state that only exists after _init_singleton() has run
            assert manager.get_transient_settings() is not None
            instances.append(manager)
        except Exception as e:  # noqa B902
            errors.append(f"{type(e).__name__}: {e}")

    threads = [threading.Thread(target=race) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(instances) == 8
    assert len(set(id(manager) for manager in instances)) == 1


def test_has_cls():
    assert _ManagerSingleton.has_cls(MPManager) is False
    MPManager()
    assert _ManagerSingleton.has_cls(MPManager) is True


def test_remove_cls():
    assert _ManagerSingleton.has_cls(MPManager) is False
    MPManager()
    assert _ManagerSingleton.has_cls(MPManager) is True
    _ManagerSingleton.remove_cls(MPManager)
    assert _ManagerSingleton.has_cls(MPManager) is False


def test_init_singleton_once():
    with patch("siliconcompiler.utils.multiprocessing.MPManager._init_singleton") as singleton:
        MPManager() is MPManager()
        singleton.assert_called_once()
        _ManagerSingleton.remove_cls(MPManager)

    # Create MPManager to avoid cleanup issue
    MPManager()


def test_get_manager():
    man0 = MPManager().get_manager()
    man1 = MPManager().get_manager()

    assert man0 is man1


def test_get_dasboard():
    dash0 = MPManager().get_dashboard()
    dash1 = MPManager().get_dashboard()

    assert dash0 is dash1
    assert isinstance(dash0, Board)


def test_get_settings():
    sett0 = MPManager().get_settings()
    sett1 = MPManager().get_settings()

    assert sett0 is sett1
    assert isinstance(sett0, SettingsManager)


def test_get_transient_settings():
    sett0 = MPManager().get_transient_settings()
    sett1 = MPManager().get_transient_settings()

    assert sett0 is sett1
    assert isinstance(sett0, SettingsManager)


def test_get_transient_settings_not_settings():
    sett0 = MPManager().get_settings()
    sett1 = MPManager().get_transient_settings()

    assert sett0 is not sett1


def test_logger(monkeypatch):
    monkeypatch.setattr(MPManager, "_MPManager__ENABLE_LOGGER", True)

    new_logger = logging.getLogger("siliconcompiler_test_logger")
    with patch("logging.getLogger") as getlogger:
        getlogger.return_value = new_logger
        logger = MPManager().logger()
        getlogger.assert_called_once_with("siliconcompiler")
    assert isinstance(logger, logging.Logger)
    assert logger is new_logger
    assert logger.name == "siliconcompiler_test_logger"
    assert logging.getLevelName(logger.level) == "INFO"
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.FileHandler)
    assert logger.handlers[0].baseFilename == MPManager()._MPManager__logfile
    assert logging.getLevelName(logger.handlers[0].level) == "WARNING"


def test_logger_except(monkeypatch):
    monkeypatch.setattr(MPManager, "_MPManager__ENABLE_LOGGER", True)

    with patch("os.makedirs") as mkdirs:
        def raise_error(*args):
            raise NotImplementedError

        mkdirs.side_effect = raise_error
        MPManager().logger()
        mkdirs.assert_called_once()


def test_logger_no_enable(monkeypatch):
    monkeypatch.setattr(MPManager, "_MPManager__ENABLE_LOGGER", False)

    new_logger = logging.getLogger("siliconcompiler_test_logger_no_enable")
    with patch("logging.getLogger") as getlogger:
        getlogger.return_value = new_logger
        logger = MPManager().logger()
        getlogger.assert_called_once_with("siliconcompiler")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "siliconcompiler_test_logger_no_enable"
    assert logging.getLevelName(logger.level) == "NOTSET"
    assert len(logger.handlers) == 0


def test_error_no_msg(monkeypatch, caplog):
    monkeypatch.setattr(MPManager(), "_MPManager__logger", logging.getLogger())
    assert MPManager()._MPManager__error is False
    MPManager().error()
    assert MPManager()._MPManager__error is True
    assert "Error occurred" in caplog.text


def test_error_with_msg(monkeypatch, caplog):
    monkeypatch.setattr(MPManager(), "_MPManager__logger", logging.getLogger())
    assert MPManager()._MPManager__error is False
    MPManager().error("This error happened here")
    assert MPManager()._MPManager__error is True
    assert "Error: This error happened here" in caplog.text


def test_stop_no_error():
    with patch("os.remove") as remove:
        MPManager().stop()
        remove.assert_called_once()


def test_stop_with_error():
    with patch("os.remove") as remove:
        MPManager().error()
        MPManager().stop()
        remove.assert_not_called()


def test_stop_handle_except():
    with patch("os.remove") as remove:
        def raise_error(*args):
            raise NotImplementedError

        remove.side_effect = raise_error
        MPManager().stop()
        remove.assert_called_once()


def test_stop_stop_dashboard():
    dashboard = MPManager().get_dashboard()
    dashboard.stop()

    with patch("siliconcompiler.report.dashboard.cli.board.Board.stop") as stop:
        assert MPManager()._MPManager__board is not None
        MPManager().stop()
        assert MPManager()._MPManager__board is None
        stop.assert_called_once()


def test_stop_dashboard_without_the_manager():
    '''The terminal is given back even when the manager's server, which holds
    the board lock, cannot be reached -- a pool worker exiting after its proxies
    were dropped, or a server that has gone.'''
    MPManager().get_dashboard()

    class Unreachable:
        def __enter__(self):
            raise ConnectionRefusedError("server gone")

        def __exit__(self, *args):
            return False

    manager = MPManager()
    with patch.object(manager, "_MPManager__board_lock", Unreachable()), \
            patch("siliconcompiler.report.dashboard.cli.board.Board.stop") as stop:
        MPManager.stop()
        stop.assert_called_once_with(force=True, dump_log=False)


def test_stop_runs_from_multiprocessing_exit():
    '''stop() is also a multiprocessing exit hook, which is how a pool worker
    leaves; atexit is not run there on every Python. It goes once stop() has run.'''
    manager = MPManager()
    hook = manager._MPManager__exit_hook
    assert hook.still_active()

    hook()
    assert not _ManagerSingleton.has_cls(MPManager)
    assert not hook.still_active()


def test_stop_repeat():
    manager = MPManager()
    manager.stop()
    manager.stop()


def _raise_kbi(*args, **kwargs):
    raise KeyboardInterrupt()


def test_stop_swallows_keyboard_interrupt_in_os_remove():
    '''A KeyboardInterrupt raised by os.remove during atexit must not escape.'''
    MPManager()
    with patch("os.remove", side_effect=_raise_kbi):
        # Must not raise.
        MPManager.stop()
    # Singleton fully cleaned up so a second stop() is a no-op.
    assert _ManagerSingleton.has_cls(MPManager) is False
    MPManager.stop()


def test_stop_swallows_keyboard_interrupt_in_handler_close():
    '''A KeyboardInterrupt raised while closing a logger handler must not escape.'''
    manager = MPManager()

    class KBIHandler(logging.Handler):
        def close(self):
            raise KeyboardInterrupt()

    manager._MPManager__logger.addHandler(KBIHandler())

    MPManager.stop()
    assert _ManagerSingleton.has_cls(MPManager) is False


def test_stop_swallows_keyboard_interrupt_in_board_stop():
    '''A KeyboardInterrupt raised while stopping the dashboard must not escape.'''
    MPManager().get_dashboard()

    with patch("siliconcompiler.report.dashboard.cli.board.Board.stop",
               side_effect=_raise_kbi):
        MPManager.stop()
    assert _ManagerSingleton.has_cls(MPManager) is False


# Needs a manager it owns: shutdown() is bound by BaseManager.start(), so a
# manager that merely connected to conftest's shared server has no such
# attribute for patch.object to replace.
@pytest.mark.isolated_manager
def test_stop_swallows_keyboard_interrupt_in_manager_shutdown():
    '''A KeyboardInterrupt raised while shutting down the multiprocessing
    manager must not escape.'''
    manager = MPManager()
    # Force the manager_server branch on so shutdown() is reached.
    manager._MPManager__manager_server = True

    with patch.object(manager._MPManager__manager, "shutdown",
                      side_effect=_raise_kbi):
        MPManager.stop()
    assert _ManagerSingleton.has_cls(MPManager) is False


def _make_log_record():
    return logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello", args=None, exc_info=None,
    )


@pytest.mark.parametrize("exc", [
    BrokenPipeError("broken"),
    EOFError("eof"),
    ConnectionResetError("reset"),
    OSError("oserr"),
    RemoteError("remote"),
])
def test_mp_queue_handler_swallows_shutdown_errors(exc):
    '''Errors raised by the underlying queue during shutdown must not escape
    enqueue(); the parent's SyncManager may have gone away before children
    finished logging.'''
    class BrokenQueue:
        def put_nowait(self, record):
            raise exc

    handler = MPQueueHandler(BrokenQueue())
    # Must not raise.
    handler.enqueue(_make_log_record())


def test_mp_queue_handler_other_errors_propagate():
    '''Errors that are not shutdown-related still propagate so genuine bugs
    are not silently hidden.'''
    class WeirdQueue:
        def put_nowait(self, record):
            raise ValueError("bug")

    handler = MPQueueHandler(WeirdQueue())
    with pytest.raises(ValueError):
        handler.enqueue(_make_log_record())


def test_stop_runs_housekeeping_after_interrupt():
    '''Even if cleanup is interrupted, atexit.unregister must still run so the
    handler is not left registered for a second invocation.'''
    MPManager()
    with patch("os.remove", side_effect=_raise_kbi), \
            patch("atexit.unregister") as unreg:
        MPManager.stop()
        unreg.assert_called_once_with(MPManager.stop)
    assert _ManagerSingleton.has_cls(MPManager) is False


@pytest.mark.parametrize("func", ["fork", "forkpty"])
def test_forking_suppresses_fork_thread_warning(func):
    message = f"This process (pid=1) is multi-threaded, use of {func}() may " \
              "lead to deadlocks in the child."
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with forking():
            warnings.warn(message, DeprecationWarning, stacklevel=2)
    assert caught == []


def test_forking_propagates_unrelated_warnings():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with forking():
            warnings.warn("an unrelated deprecation", DeprecationWarning, stacklevel=2)
            warnings.warn("a user warning", UserWarning, stacklevel=2)
    messages = [str(w.message) for w in caught]
    assert "an unrelated deprecation" in messages
    assert "a user warning" in messages


def test_forking_restores_filters_after_normal_exit():
    before = warnings.filters[:]
    with forking():
        pass
    assert warnings.filters == before


def test_forking_restores_filters_after_exception():
    before = warnings.filters[:]
    with pytest.raises(RuntimeError, match=r"^boom$"):
        with forking():
            raise RuntimeError("boom")
    assert warnings.filters == before


@pytest.fixture
def guarded(tmp_path):
    """The file a test locks; its lock file is this plus ``.lock``."""
    return str(tmp_path / "file")


def test_get_file_lock_is_shared_per_file(guarded, tmp_path):
    """Every caller in the process gets the one lock for a file, however it is named."""
    lock = get_file_lock(guarded)
    assert get_file_lock(guarded) is lock
    assert get_file_lock(tmp_path / "file") is lock
    assert get_file_lock(os.path.join(str(tmp_path), ".", "file")) is lock
    assert get_file_lock(str(tmp_path / "other")) is not lock


def test_file_lock_names_its_files(tmp_path):
    """Callers name the file they lock; the lock names the files that lock it."""
    lock = get_file_lock(tmp_path / "entry")
    assert lock.path == str(tmp_path / "entry")
    assert lock.lock_path == str(tmp_path / "entry.lock")
    assert lock.fallback_path == str(tmp_path / "entry.sc_lock")
    assert lock.paths == (lock.lock_path, lock.fallback_path)
    assert not os.path.exists(lock.lock_path), "naming the files created one"

    with lock.locked(1):
        assert os.path.exists(lock.lock_path)


def test_file_lock_excludes_another_thread(guarded):
    """
    fcntl alone would let a second thread straight in: its lock is per process.
    """
    holding = threading.Event()
    release = threading.Event()

    def holder():
        with get_file_lock(guarded).locked(10):
            holding.set()
            release.wait(timeout=10)

    thread = threading.Thread(target=holder)
    thread.start()
    try:
        assert holding.wait(timeout=10)
        with pytest.raises(FileLockTimeout, match=r"another thread of this process holds it$"):
            get_file_lock(guarded).acquire(0)
        with pytest.raises(FileLockTimeout, match=r"another thread of this process holds it$"):
            with get_file_lock(guarded).locked(0.1):
                pytest.fail("should not get here")
    finally:
        release.set()
        thread.join(timeout=10)

    get_file_lock(guarded).acquire(0)
    get_file_lock(guarded).release()


def test_file_lock_timeout_covers_the_thread_wait(guarded):
    """A short timeout is not stretched by a long holder in this process."""
    holding = threading.Event()
    release = threading.Event()

    def holder():
        with get_file_lock(guarded).locked(10):
            holding.set()
            release.wait(timeout=10)

    thread = threading.Thread(target=holder)
    thread.start()
    try:
        assert holding.wait(timeout=10)
        start = time.monotonic()
        with pytest.raises(FileLockTimeout):
            get_file_lock(guarded).acquire(0.2)
        assert time.monotonic() - start < 5
    finally:
        release.set()
        thread.join(timeout=10)


def test_file_lock_excludes_another_process(guarded, other_process_lock):
    with get_file_lock(guarded).locked(10):
        assert not other_process_lock.can_take(get_file_lock(guarded).lock_path)
    assert other_process_lock.can_take(get_file_lock(guarded).lock_path)

    with other_process_lock.hold(get_file_lock(guarded).lock_path):
        with pytest.raises(FileLockTimeout, match=r": another process holds it$"):
            with get_file_lock(guarded).locked(0.2):
                pytest.fail("should not get here")


def test_file_lock_is_reentrant(guarded, other_process_lock):
    """
    An inner release must not drop the outer hold: with fcntl it would, for the
    whole process.
    """
    lock = get_file_lock(guarded)
    with lock.locked(10):
        with lock.locked(10):
            pass
        assert not other_process_lock.can_take(get_file_lock(guarded).lock_path)
    assert other_process_lock.can_take(get_file_lock(guarded).lock_path)


def test_file_lock_held_without_a_reference(guarded, other_process_lock):
    """
    A held lock nobody kept a reference to is not collected: that would close
    its file, and with it the file lock.
    """
    get_file_lock(guarded).acquire(0)
    gc.collect()
    try:
        assert not other_process_lock.can_take(get_file_lock(guarded).lock_path)
    finally:
        get_file_lock(guarded).release()
    assert other_process_lock.can_take(get_file_lock(guarded).lock_path)


def test_file_lock_release_without_a_hold(guarded, other_process_lock):
    """
    A stray release changes nothing. It used to leave the hold count at -1, so
    the next acquire skipped taking the file lock and held nothing.
    """
    lock = get_file_lock(guarded)
    with pytest.raises(RuntimeError, match=r"is not held by this thread$"):
        lock.release()

    with lock.locked(1):
        assert not other_process_lock.can_take(lock.lock_path)
    assert other_process_lock.can_take(lock.lock_path)


def test_file_lock_release_from_another_thread(guarded, other_process_lock):
    """
    Only the holder releases. Another thread's release used to drop the file
    lock out from under the holder before it was refused.
    """
    lock = get_file_lock(guarded)
    errors = []

    def release():
        try:
            lock.release()
        except RuntimeError as e:
            errors.append(str(e))

    with lock.locked(1):
        thread = threading.Thread(target=release)
        thread.start()
        thread.join(timeout=10)
        assert len(errors) == 1 and errors[0].endswith("is not held by this thread")
        assert not other_process_lock.can_take(lock.lock_path), "the holder lost the file lock"
    assert other_process_lock.can_take(lock.lock_path)


def test_file_lock_waits_without_a_timeout(guarded):
    holding = threading.Event()

    def holder():
        with get_file_lock(guarded).locked(10):
            holding.set()
            time.sleep(0.2)

    thread = threading.Thread(target=holder)
    thread.start()
    assert holding.wait(timeout=10)
    with get_file_lock(guarded).locked():
        pass
    thread.join(timeout=10)


def test_file_lock_timeout_message():
    """The timeout acquire() passes through may be None."""
    timed = FileLockTimeout("/a/file", 0.5, "another process holds it")
    assert str(timed) == "Timed out after 0.5s waiting for the lock on /a/file: " \
        "another process holds it"
    assert timed.timeout == 0.5

    unlimited = FileLockTimeout("/a/file", None, "another process holds it")
    assert str(unlimited) == "Timed out waiting for the lock on /a/file: " \
        "another process holds it"
    assert unlimited.timeout is None


@pytest.fixture
def no_flock():
    """Make every lockf fail, as on an NFS mount without lock support."""
    with patch("fasteners.InterProcessLock.acquire", side_effect=RuntimeError("ENOLCK")):
        yield


def test_file_lock_follows_a_symlink(tmp_path):
    """One file, one lock, however it is spelled; its files sit beside the file."""
    target = tmp_path / "real" / "settings.json"
    target.parent.mkdir()
    target.write_text("{}")
    link = tmp_path / "settings.json"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create a symlink here")

    lock = get_file_lock(link)
    assert get_file_lock(target) is lock
    assert lock.path == os.path.realpath(target)
    assert lock.lock_path == os.path.realpath(target) + ".lock"


def test_file_lock_resolves_its_own_path(tmp_path, monkeypatch):
    """Built directly, as well as through get_file_lock()."""
    monkeypatch.chdir(tmp_path)
    lock = FileLock(os.path.join("sub", "..", "entry"))
    assert lock.path == os.path.realpath(tmp_path / "entry")
    assert lock.lock_path == lock.path + ".lock"


def test_file_lock_fallback_taken(guarded):
    lock = get_file_lock(guarded)
    assert lock.fallback_taken() is None

    with open(lock.fallback_path, "w"):
        pass
    os.utime(lock.fallback_path, (1000, 1000))
    assert lock.fallback_taken() == 1000


def test_file_lock_fallback_held_by_marker(guarded, no_flock):
    lock = get_file_lock(guarded)
    with lock.locked(1):
        assert os.path.exists(lock.fallback_path)
        with lock.locked(1):
            pass
        assert os.path.exists(lock.fallback_path), "the inner release dropped the outer hold"
    assert not os.path.exists(lock.fallback_path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_file_lock_fallback_marker_is_private(guarded, no_flock):
    """Owner-only whatever the umask: never wider than a lock taken with a mode."""
    previous = os.umask(0o022)
    try:
        lock = get_file_lock(guarded)
        with lock.locked(1):
            assert stat.S_IMODE(os.stat(lock.fallback_path).st_mode) == 0o600
    finally:
        os.umask(previous)


def test_file_lock_fallback_marker_excludes(guarded, no_flock):
    """
    A marker that exists is a hold by someone else, or a killed process's
    residue: either way, wait, and on timeout say which file to delete.
    """
    lock = get_file_lock(guarded)
    with open(lock.fallback_path, "w"):
        pass

    start = time.monotonic()
    with pytest.raises(FileLockTimeout, match=r"sc_lock exists\. .* delete it if no process "
                                              r"is using it$") as e:
        lock.acquire(0.2)
    assert time.monotonic() - start < 5, "a fractional timeout was not honoured"
    assert e.value.fallback == lock.fallback_path
    assert os.path.exists(lock.fallback_path), "someone else's marker was removed"

    os.remove(lock.fallback_path)
    with lock.locked(1):
        pass


def test_file_lock_fallback_excludes_another_thread(guarded, no_flock):
    holding = threading.Event()
    release = threading.Event()

    def holder():
        with get_file_lock(guarded).locked(10):
            holding.set()
            release.wait(timeout=10)

    thread = threading.Thread(target=holder)
    thread.start()
    try:
        assert holding.wait(timeout=10)
        with pytest.raises(FileLockTimeout, match=r"another thread of this process holds it$"):
            get_file_lock(guarded).acquire(0.1)
    finally:
        release.set()
        thread.join(timeout=10)


def test_file_lock_fallback_failure_releases_thread_lock(guarded, no_flock, monkeypatch):
    """Where not even the marker can be created, nothing is left held."""
    lock = get_file_lock(guarded)
    real_open = os.open

    def no_marker(path, *args, **kwargs):
        if str(path).endswith(".sc_lock"):
            raise PermissionError("read-only")
        return real_open(path, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(os, "open", no_marker)
        with pytest.raises(PermissionError, match=r"^read-only$"):
            lock.acquire(0)

    done = []

    def take():
        with lock.locked(0):
            done.append(True)

    thread = threading.Thread(target=take)
    thread.start()
    thread.join(timeout=10)
    assert done == [True]


def test_fasteners_is_only_used_by_file_lock():
    """
    Lock a file through get_file_lock(), never a fasteners lock of your own: on
    POSIX that lock is held per process, so it walks into every other lock on
    the same file in this process (see FileLock).
    """
    import siliconcompiler
    root = os.path.dirname(siliconcompiler.__file__)
    allowed = os.path.join(root, "utils", "multiprocessing.py")

    offenders = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if not filename.endswith(".py") or path == allowed:
                continue
            with open(path, encoding="utf-8") as f:
                for number, line in enumerate(f, start=1):
                    if re.match(r"\s*(import fasteners|from fasteners\b)", line):
                        offenders.append(f"{os.path.relpath(path, root)}:{number}")

    assert offenders == []


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires fork")
def test_file_locks_reset_after_fork(guarded, wait_for_child):
    """
    A child forked while a thread holds a lock does not wait on that thread,
    which it does not have: it waits on the parent, like any other process.
    """
    holding = threading.Event()
    release = threading.Event()

    def holder():
        with get_file_lock(guarded).locked(10):
            holding.set()
            release.wait(timeout=10)

    thread = threading.Thread(target=holder)
    thread.start()
    assert holding.wait(timeout=10)

    with forking():
        pid = os.fork()
    if pid == 0:
        try:
            with get_file_lock(guarded).locked(0.2):
                os._exit(2)
        except FileLockTimeout as e:
            os._exit(0 if str(e).endswith(": another process holds it") else 3)
        except BaseException:
            os._exit(1)

    try:
        exited, waited_on_parent = wait_for_child(pid)
    finally:
        release.set()
        thread.join(timeout=10)

    assert exited, "forked child hung on the lock"
    assert waited_on_parent, "forked child did not wait on the parent process's lock"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires fork")
def test_shared_group_proxy_rebuilt_after_fork(wait_for_child):
    """A forked child builds its own group proxy, even when a parent thread
    held the group lock across the fork."""
    first = MPManager.get_shared_group("dashboard")
    assert first is not None
    assert MPManager.get_shared_group("dashboard") is first

    with MPManager()._MPManager__group_lock:
        with forking():
            pid = os.fork()
        if pid == 0:
            try:
                group = MPManager.get_shared_group("dashboard")
                os._exit(0 if group is not None and group is not first else 2)
            except BaseException:
                os._exit(1)

    exited, rebuilt = wait_for_child(pid)
    assert exited, "forked child hung on the inherited group lock"
    assert rebuilt


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires fork")
@pytest.mark.parametrize("flock", (True, False), ids=("flock", "no_flock"))
def test_file_lock_inherited_hold_stays_with_the_parent(guarded, flock, other_process_lock,
                                                        wait_for_child):
    """
    A child forked by the holding thread inherits the hold, and leaves it on its
    way out without releasing what is the parent's. Where files cannot be locked
    that is the marker, which the child used to delete from under the parent.
    """
    lock = get_file_lock(guarded)
    no_flock = patch("fasteners.InterProcessLock.acquire", side_effect=RuntimeError("ENOLCK"))

    pid = None
    try:
        with contextlib.nullcontext() if flock else no_flock:
            with lock.locked(1):
                with forking():
                    pid = os.fork()
                if pid:
                    exited, clean = wait_for_child(pid)
                    if flock:
                        held = not other_process_lock.can_take(lock.lock_path)
                    else:
                        held = os.path.exists(lock.fallback_path)
    except BaseException:
        if pid == 0:
            os._exit(1)
        raise
    if pid == 0:
        os._exit(0)

    assert exited and clean, "the child failed to leave its inherited hold"
    assert held, "the child released the parent's lock"
    if not flock:
        assert not os.path.exists(lock.fallback_path), "the parent did not release its marker"


@pytest.fixture
def group():
    return SharedGroup("test")


def test_claim_is_exclusive(group):
    assert group.claim(100) is True
    assert group.claim(200) is False
    # Idempotent for the holder, so a member that re-enters the group (a second
    # run in the same process) does not lose the role it already has.
    assert group.claim(100) is True
    assert group.owner() == 100


def test_release_frees_the_role(group):
    assert group.claim(100) is True
    group.release(100)
    assert group.owner() is None
    assert group.claim(200) is True


def test_release_by_a_non_holder_is_ignored(group):
    assert group.claim(100) is True
    group.release(200)
    assert group.owner() == 100


@pytest.mark.parametrize("alive", (False, True), ids=("dead", "stalled"))
def test_stale_owner_loses_the_role_only_once_gone(group, monkeypatch, alive):
    """An owner whose process died lapses after its heartbeat goes stale; one
    still alive keeps the role, or it would paint beside its successor."""
    monkeypatch.setattr(SharedGroup, "OWNER_TIMEOUT", 0.05)
    owner = os.getpid() if alive else _dead_pid()
    assert group.claim(owner) is True

    time.sleep(0.1)
    assert group.owner() == (owner if alive else None)
    assert group.claim(_dead_pid()) is not alive


def test_publish_and_collect_round_trip(group):
    assert group.claim(1) is True

    assert group.publish(2, {"key2": "snap2"}, ["a", "b"]) is True
    assert group.publish(3, {"key3": "snap3"}, ["c"]) is True

    state, stream, orphaned = group.collect(1)
    assert state == {"key2": "snap2", "key3": "snap3"}
    assert stream == ["a", "b", "c"]
    assert orphaned == []

    # Everything already handed over is gone; only new publishes come back.
    assert group.collect(1) == ({}, [], [])

    assert group.publish(2, {"key2": "snap2-updated"}, []) is True
    state, stream, _ = group.collect(1)
    assert state == {"key2": "snap2-updated"}
    assert stream == []


def test_collect_by_a_non_owner_returns_none(group):
    assert group.claim(1) is True
    group.publish(2, {"key2": "snap"}, [])

    # Signals "you are not the owner, step down" rather than handing state to
    # a member that is not acting on it.
    assert group.collect(2) is None
    # ... and it is still there for the real owner.
    assert group.collect(1)[0] == {"key2": "snap"}


def test_collect_is_the_owner_heartbeat(group, monkeypatch):
    owner = _dead_pid()
    assert group.claim(owner) is True
    monkeypatch.setattr(SharedGroup, "OWNER_TIMEOUT", 0.05)

    for _ in range(4):
        time.sleep(0.02)
        assert group.collect(owner) is not None, "heartbeat should keep the role alive"
        assert group.owner() == owner

    time.sleep(0.1)
    assert group.owner() is None


def test_publish_reports_whether_an_owner_is_live(group):
    # Nobody owns it yet: the member needs to know so it can take over.
    assert group.publish(2, {}, []) is False

    assert group.claim(1) is True
    assert group.publish(2, {}, []) is True

    group.release(1)
    assert group.publish(2, {}, []) is False


def test_owner_own_state_is_not_echoed_back(group):
    """The owner is not handed back what it published itself, which would overwrite
    its fresher local state."""
    assert group.claim(1) is True
    group.publish(1, {"mine": "stale"}, [])
    group.publish(2, {"theirs": "fresh"}, [])

    state, _, _ = group.collect(1)
    assert state == {"theirs": "fresh"}


def test_silent_member_is_reported_orphaned(group, monkeypatch):
    """A silent member's keys are reported orphaned once, keeping their last value,
    and are live again when it publishes."""
    assert group.claim(1) is True
    group.publish(2, {"gone": "snap"}, [])
    assert group.collect(1)[2] == []

    monkeypatch.setattr(SharedGroup, "MEMBER_TIMEOUT", -1.0)
    assert group.collect(1)[2] == ["gone"]

    # Reported once, not on every collect from then on.
    assert group.collect(1)[2] == []

    # A member that comes back is live again.
    group.publish(2, {"gone": "snap2"}, [])
    monkeypatch.setattr(SharedGroup, "MEMBER_TIMEOUT", 30.0)
    state, _, orphaned = group.collect(1)
    assert state == {"gone": "snap2"}
    assert orphaned == []


def test_owner_is_never_reported_orphaned(group, monkeypatch):
    assert group.claim(1) is True
    group.publish(1, {"mine": "snap"}, [])
    monkeypatch.setattr(SharedGroup, "MEMBER_TIMEOUT", -1.0)
    assert group.collect(1)[2] == []


def test_stream_is_bounded(group, monkeypatch):
    monkeypatch.setattr(SharedGroup, "MAX_STREAM", 10)

    group.publish(2, {}, [f"entry{i}" for i in range(25)])
    group.claim(1)
    _, stream, _ = group.collect(1)

    # Oldest dropped, newest kept in order: an owner that attaches late must
    # not be handed an unbounded backlog.
    assert stream == [f"entry{i}" for i in range(15, 25)]


def test_state_is_bounded(group, monkeypatch):
    """Retained state is capped, evicting the key published least recently: one
    that keeps publishing, like a run still going, outlasts later ones."""
    monkeypatch.setattr(SharedGroup, "MAX_KEYS", 4)

    for i in range(10):
        group.publish(2, {f"key{i}": f"snap{i}"}, [])
    group.publish(2, {"key6": "snap6-again"}, [])
    group.publish(2, {"key10": "snap10"}, [])

    group.claim(1)
    state, _, _ = group.collect(1)
    assert sorted(state) == ["key10", "key6", "key8", "key9"]


def test_new_owner_is_handed_what_the_last_one_collected(group, monkeypatch):
    """A new owner gets every retained snapshot and every orphan, not only what
    changes after it takes over."""
    group.claim(1)
    group.publish(2, {"live": "running"}, [])
    group.publish(3, {"gone": "running"}, [])
    group.collect(1)
    group.publish(2, {}, [])
    monkeypatch.setattr(group, "_SharedGroup__seen", {2: time.time(), 3: 0.0})
    assert group.collect(1)[2] == ["gone"]
    group.release(1)

    assert group.claim(4) is True
    state, _, orphaned = group.collect(4)
    assert state == {"live": "running", "gone": "running"}
    assert orphaned == ["gone"]
    assert group.collect(4) == ({}, [], [])


def test_evicted_key_is_still_retired(group, monkeypatch):
    """A member whose snapshot was evicted is still reported once it goes silent."""
    monkeypatch.setattr(SharedGroup, "MAX_KEYS", 1)
    group.claim(1)
    group.publish(2, {"old": "running"}, [])
    group.publish(3, {"new": "running"}, [])
    group.collect(1)

    monkeypatch.setattr(SharedGroup, "MEMBER_TIMEOUT", -1.0)
    assert sorted(group.collect(1)[2]) == ["new", "old"]


def test_groups_are_per_name_singletons():
    """Every process gets the same group for a name, and different names never share one."""
    assert get_shared_group("dashboard") is get_shared_group("dashboard")
    assert get_shared_group("dashboard") is not get_shared_group("scheduler")
    assert isinstance(get_shared_group("dashboard"), SharedGroup)
    assert get_shared_group("scheduler").name() == "scheduler"


def test_manager_registers_the_shared_group():
    """The typeid must exist on the manager, or nothing below can work."""
    assert "shared_group" in _sync_manager_class()._registry
    # Registered on the subclass only: an unrelated SyncManager built by user
    # code must not grow SiliconCompiler's types.
    from multiprocessing.managers import SyncManager
    assert "shared_group" not in SyncManager._registry


def _publisher(address, tag, count):
    MPManager._set_manager_address(address)
    group = MPManager.get_shared_group("spawned")
    for i in range(count):
        group.publish(os.getpid(), {f"design{tag}/job0": f"snap-{tag}-{i}"}, [f"[{tag}] {i}"])
        time.sleep(0.02)


def test_group_spans_spawned_processes():
    """Spawned members publish and one owner collects, over a real manager proxy:
    the shape of a ProcessPoolExecutor sweep."""
    # Not "dashboard": the session's server keeps a group for the whole run,
    # and a later test's renderer would be handed these keys.
    group = MPManager.get_shared_group("spawned")
    assert group is not None, "manager must provide a shared group"
    # Cached per name and process, so a loop does not build a proxy per tick.
    assert MPManager.get_shared_group("spawned") is group

    assert group.claim(os.getpid()) is True

    ctx = multiprocessing.get_context("spawn")
    address = MPManager._get_manager_address()
    procs = [ctx.Process(target=_publisher, args=(address, tag, 5)) for tag in ("A", "B")]
    for proc in procs:
        proc.start()

    state, stream = {}, []
    deadline = time.time() + 60
    while time.time() < deadline and len(state) < 2:
        collected = group.collect(os.getpid())
        assert collected is not None
        state.update(collected[0])
        stream.extend(collected[1])
        time.sleep(0.02)

    for proc in procs:
        proc.join(timeout=60)
        assert proc.exitcode == 0

    collected = group.collect(os.getpid())
    state.update(collected[0])
    stream.extend(collected[1])

    assert sorted(state) == ["designA/job0", "designB/job0"]
    assert len(stream) == 10
    assert sorted(stream) == [f"[{tag}] {i}" for tag in ("A", "B") for i in range(5)]

    group.release(os.getpid())


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    pid = proc.pid
    del proc
    # On Windows an exited process stays listed until the last handle to it
    # closes, so wait for it to go, as psutil's own wait() does.
    deadline = time.monotonic() + 10
    while psutil.pid_exists(pid) and time.monotonic() < deadline:
        time.sleep(0.01)
    return pid


def _wait_for_exit(process, timeout: float = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not process.is_alive():
            return True
        time.sleep(0.1)
    return False


def test_clients_not_closing_before_first_attach():
    """A server that has not been joined yet is starting up, not abandoned."""
    clients = _ManagerClients()
    assert clients.sweep() is False
    assert clients.attach("first", os.getpid()) is True


def test_clients_close_with_the_last_detach():
    clients = _ManagerClients()
    assert clients.attach("a", os.getpid())
    # Same pid, separate token: one process holds several managers in turn,
    # and the detach of one must not drop the other.
    assert clients.attach("b", os.getpid())

    assert clients.detach("a") == 1
    assert clients.sweep() is False

    assert clients.detach("b") == 0
    assert clients.sweep() is True


def test_clients_refuse_attach_once_closing():
    """A late arrival starts its own server instead of joining a dying one."""
    clients = _ManagerClients()
    clients.attach("a", os.getpid())
    clients.detach("a")

    assert clients.attach("late", os.getpid()) is False


def test_clients_sweep_drops_the_dead():
    clients = _ManagerClients()
    clients.attach("dead", _dead_pid())
    assert clients.sweep() is True, "a server whose only client died must close"

    clients = _ManagerClients()
    clients.attach("dead", _dead_pid())
    clients.attach("live", os.getpid())
    assert clients.sweep() is False
    assert clients.detach("live") == 0


def test_process_alive_rejects_reused_pid():
    created = _process_created(os.getpid())
    assert created is not None
    assert _process_alive(os.getpid(), created)
    assert not _process_alive(os.getpid(), created - 1000)
    assert not _process_alive(_dead_pid(), None)


def test_environment_round_trip(monkeypatch):
    value = MPManager._MPManager__environment_value("/tmp/socket")
    monkeypatch.setenv(MANAGER_ENVIRONMENT, value)
    assert MPManager._address_from_environment() == "/tmp/socket"


def test_environment_tcp_address_is_a_tuple(monkeypatch):
    value = MPManager._MPManager__environment_value(("localhost", 1234))
    monkeypatch.setenv(MANAGER_ENVIRONMENT, value)
    assert MPManager._address_from_environment() == ("localhost", 1234)


@pytest.mark.parametrize("value", [
    "",
    "not json",
    json.dumps({"address": "/tmp/socket"}),
    json.dumps({"compatibility": []}),
    json.dumps(["/tmp/socket"]),
])
def test_environment_unreadable_is_ignored(monkeypatch, value):
    monkeypatch.setenv(MANAGER_ENVIRONMENT, value)
    assert MPManager._address_from_environment() is None


@pytest.mark.parametrize("field", [0, 1, 2], ids=["host", "siliconcompiler", "python"])
def test_environment_incompatible_is_ignored(monkeypatch, field):
    """An address that travelled to another host or install is not tried."""
    entry = json.loads(MPManager._MPManager__environment_value("/tmp/socket"))
    entry["compatibility"][field] = "something else"
    monkeypatch.setenv(MANAGER_ENVIRONMENT, json.dumps(entry))
    assert MPManager._address_from_environment() is None


def test_terminal_rendezvous_names_host_and_terminal(monkeypatch):
    monkeypatch.setattr(os, "ttyname", lambda fd: "/dev/pts/7", raising=False)
    host = multiprocessing_utils.socket.gethostname()
    assert _terminal_rendezvous() == os.path.join(default_manager_dir(), f"{host}-pts-7.json")


def test_terminal_rendezvous_needs_a_terminal(monkeypatch):
    def not_a_terminal(fd):
        raise OSError("Inappropriate ioctl for device")

    monkeypatch.setattr(os, "ttyname", not_a_terminal, raising=False)
    assert _terminal_rendezvous() is None


@pytest.mark.isolated_manager
def test_stale_terminal_rendezvous_is_replaced(monkeypatch):
    """A file naming a server that has gone is overwritten, not obeyed, and the
    server that replaced it takes it back out when it shuts down."""
    path = os.path.abspath("rendezvous.json")
    monkeypatch.setattr(multiprocessing_utils, "_terminal_rendezvous", lambda: path)
    with open(path, "w") as f:
        f.write(MPManager._MPManager__environment_value(os.path.abspath("gone.sock")))

    manager = MPManager()
    assert manager._MPManager__manager_server
    with open(path) as f:
        assert MPManager._MPManager__address_from_value(f.read()) == \
            MPManager._get_manager_address()

    MPManager.stop()
    assert not os.path.exists(path)


# Joins through the terminal alone: no environment, no address handed over.
_SIBLING = """
import sys
import siliconcompiler.utils.multiprocessing as mp
mp._terminal_rendezvous = lambda: sys.argv[1]
mp.MPManager._MPManager__ENABLE_LOGGER = False
manager = mp.MPManager()
print("server" if manager._MPManager__manager_server else "client", flush=True)
print(repr(mp.MPManager._get_manager_address()), flush=True)
sys.stdin.readline()
"""


@pytest.mark.timeout(60)
def test_siblings_meet_through_terminal():
    """The workers of a pool whose parent never started a manager -- each
    building its own Project -- share one server, so they share one dashboard.
    Started together, so the rendezvous lock is what keeps them to one."""
    path = os.path.abspath("rendezvous.json")
    env = {key: value for key, value in os.environ.items() if key != MANAGER_ENVIRONMENT}

    siblings = [subprocess.Popen([sys.executable, "-c", _SIBLING, path], env=env,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                for _ in range(3)]
    try:
        reports = [(sibling.stdout.readline().strip(), sibling.stdout.readline().strip())
                   for sibling in siblings]
        roles = sorted(role for role, _ in reports)
        assert roles == ["client", "client", "server"]
        assert len(set(address for _, address in reports)) == 1

        for sibling in siblings:
            sibling.stdin.write("\n")
            sibling.stdin.flush()
            sibling.wait(timeout=60)
    finally:
        for sibling in siblings:
            if sibling.poll() is None:
                sibling.kill()
                sibling.wait()


# Joins through the environment alone -- no Project, no address handed over --
# then waits to be told to use the server, and again to exit.
_CHILD = """
import os
import sys
from siliconcompiler.utils.multiprocessing import MPManager
MPManager._MPManager__ENABLE_LOGGER = False
manager = MPManager()
print("server" if manager._MPManager__manager_server else "client", flush=True)
print(repr(MPManager._get_manager_address()), flush=True)
sys.stdin.readline()
group = MPManager.get_shared_group("lifetime")
print(group is not None and group.claim(os.getpid()), flush=True)
sys.stdin.readline()
"""


def _start_child():
    return subprocess.Popen([sys.executable, "-c", _CHILD],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)


def _end_child(child, how: str) -> None:
    if how == "kill":
        child.kill()
    else:
        child.stdin.write("\n")
        child.stdin.flush()
    child.wait(timeout=60)


@pytest.mark.isolated_manager
def test_server_advertises_itself_until_stopped():
    MPManager()
    process = MPManager.get_manager()._process

    assert MPManager._address_from_environment() == MPManager._get_manager_address()

    MPManager.stop()
    assert MANAGER_ENVIRONMENT not in os.environ
    assert not process.is_alive(), "with nobody else attached, stop() shuts the server down"


@pytest.mark.isolated_manager
def test_subprocess_joins_through_environment():
    MPManager()
    address = MPManager._get_manager_address()

    child = _start_child()
    try:
        assert child.stdout.readline().strip() == "client"
        assert child.stdout.readline().strip() == repr(address)
        child.stdin.write("\n")
        child.stdin.flush()
        assert child.stdout.readline().strip() == "True"
        _end_child(child, "exit")
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


@pytest.mark.isolated_manager
@pytest.mark.parametrize("how", ["exit", "kill"])
def test_server_outlives_its_starter(how):
    """The starter finishes first; the server stays for the run still going,
    then stops by itself once that run is gone -- detached or killed."""
    MPManager()
    process = MPManager.get_manager()._process

    child = _start_child()
    try:
        assert child.stdout.readline().strip() == "client"
        child.stdout.readline()

        MPManager.stop()
        time.sleep(2 * _ManagerClients.POLL)
        assert process.is_alive(), "the server must stay up while a client is attached"

        # And still serves it.
        child.stdin.write("\n")
        child.stdin.flush()
        assert child.stdout.readline().strip() == "True"

        _end_child(child, how)
        assert _wait_for_exit(process), "the server must stop once its last client is gone"
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        if process.is_alive():
            process.kill()
            process.join()


@pytest.mark.isolated_manager
def test_forked_child_stop_leaves_parent_manager():
    """A child that inherited the instance must not detach or shut down its
    parent's server on the way out."""
    MPManager()
    manager = MPManager.get_manager()
    process = manager._process

    try:
        real_pid = os.getpid()
        with patch("os.getpid", return_value=real_pid + 1):
            MPManager.stop()
        assert process.is_alive()
        # The parent is still attached.
        assert manager.manager_clients().detach("not-attached") == 1
    finally:
        manager.shutdown()
        os.environ.pop(MANAGER_ENVIRONMENT, None)
