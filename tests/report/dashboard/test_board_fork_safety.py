import queue
import threading
import types

import pytest

from rich.console import Console

from siliconcompiler.report.dashboard.cli.board import Board
from siliconcompiler.utils.multiprocessing import MPManager


@pytest.fixture(autouse=True)
def _force_terminal(monkeypatch):
    # The board only constructs its sync primitives when the console is a
    # terminal; force that so the assertions below have something to inspect.
    monkeypatch.setattr(Console, "is_terminal", True)


def test_board_sync_primitives_are_not_manager_proxies():
    """The Board's synchronization primitives are plain threading/queue objects, not SyncManager
    proxies, which deadlock a run when forked node workers share the manager's connection.
    """
    board = Board(MPManager.get_manager())
    assert board._active, "board must be active for this test to be meaningful"

    # SyncManager proxies all live in the multiprocessing.managers module.
    for name in ("_render_event", "_render_stop_event", "_board_info",
                 "_job_data", "_job_data_lock", "_log_handler_queue"):
        obj = getattr(board, name)
        assert type(obj).__module__ != "multiprocessing.managers", (
            f"Board.{name} is a SyncManager proxy ({type(obj)!r}); it must be a "
            "plain in-process primitive or it will deadlock across fork()")


def test_board_sync_primitives_are_expected_plain_types():
    board = Board(MPManager.get_manager())
    assert board._active

    assert isinstance(board._render_event, threading.Event)
    assert isinstance(board._render_stop_event, threading.Event)
    assert isinstance(board._board_info, types.SimpleNamespace)
    assert isinstance(board._job_data, dict)
    assert isinstance(board._log_handler_queue, queue.Queue)
