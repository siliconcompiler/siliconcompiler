import logging

from multiprocessing.managers import RemoteError
from unittest.mock import patch

import pytest

from siliconcompiler.utils.multiprocessing import MPManager, MPQueueHandler, \
    _ManagerSingleton, get_process_context
from siliconcompiler.report.dashboard.cli.board import Board
from siliconcompiler.utils.settings import SettingsManager


def test_get_process_context_linux(monkeypatch):
    '''On Linux the start method is pinned to fork so that unguarded
    module-level proj.run() scripts keep working regardless of the interpreter
    default (which became forkserver in Python 3.14).

    Assert on the requested method name rather than the returned context so the
    test is portable: Windows has no fork context, so actually calling
    get_context("fork") there raises ValueError.'''
    monkeypatch.setattr("sys.platform", "linux")
    with patch("siliconcompiler.utils.multiprocessing.multiprocessing.get_context") as get_ctx:
        get_process_context()
        get_ctx.assert_called_once_with("fork")


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_get_process_context_non_linux(monkeypatch, platform):
    '''Off Linux fork is either unavailable (Windows) or unsafe with threads
    (macOS), so we pin spawn explicitly rather than relying on the default.'''
    monkeypatch.setattr("sys.platform", platform)
    with patch("siliconcompiler.utils.multiprocessing.multiprocessing.get_context") as get_ctx:
        get_process_context()
        get_ctx.assert_called_once_with("spawn")


def test_init_singleton():
    man0 = MPManager()
    man1 = MPManager()

    assert man0 is man1

    assert MPManager in _ManagerSingleton._instances


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
