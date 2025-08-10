import logging

from unittest.mock import patch

from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler.report.dashboard.cli.board import Board


def test_init_singleton():
    man0 = MPManager()
    man1 = MPManager()

    assert man0 is man1


def test_init_singleton_once():
    with patch("siliconcompiler.utils.multiprocessing.MPManager._init_singleton") as singleton:
        MPManager() is MPManager()
        singleton.assert_called_once()


def test_get_manager():
    man0 = MPManager().get_manager()
    man1 = MPManager().get_manager()

    assert man0 is man1


def test_get_dasboard():
    dash0 = MPManager().get_dashboard()
    dash1 = MPManager().get_dashboard()

    assert dash0 is dash1
    assert isinstance(dash0, Board)


def test_logger():
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


def test_logger_except():
    with patch("os.makedirs") as mkdirs:
        def raise_error(*args):
            raise NotImplementedError

        mkdirs.side_effect = raise_error
        MPManager().logger()
        mkdirs.assert_called_once()


def test_logger_no_enable():
    MPManager._MPManager__ENABLE_LOGGER = False
    new_logger = logging.getLogger("siliconcompiler_test_logger_no_enable")
    with patch("logging.getLogger") as getlogger:
        getlogger.return_value = new_logger
        logger = MPManager().logger()
        getlogger.assert_called_once_with("siliconcompiler")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "siliconcompiler_test_logger_no_enable"
    assert logging.getLevelName(logger.level) == "NOTSET"
    assert len(logger.handlers) == 0


def test_error_no_msg(caplog):
    setattr(MPManager(), "_MPManager__logger", logging.getLogger())
    assert MPManager()._MPManager__error is False
    MPManager().error()
    assert MPManager()._MPManager__error is True
    assert "Error occurred" in caplog.text


def test_error_with_msg(caplog):
    setattr(MPManager(), "_MPManager__logger", logging.getLogger())
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
