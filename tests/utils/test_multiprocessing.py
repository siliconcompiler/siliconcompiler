import contextlib
import gc
import logging
import os
import re
import stat
import threading
import time
import warnings

from multiprocessing.managers import RemoteError
from unittest.mock import patch

import pytest

from siliconcompiler.utils.multiprocessing import MPManager, MPQueueHandler, \
    _ManagerSingleton, get_process_context, forking, get_file_lock, FileLock, \
    FileLockTimeout
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


# --- FileLock ---
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


# --- FileLock where the filesystem cannot lock files ---
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
