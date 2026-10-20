import os
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


def test_board_holds_no_reference_to_a_manager_proxy():
    """The cross-process group is a manager proxy, so a Board must not keep one.

    Boards are inherited by every forked node worker. The proxy that lets
    concurrent runs share one dashboard therefore lives in
    :class:`SharedGroupMember`, built lazily in ``open_dashboard()`` and backed
    by a per-process cache in ``MPManager.get_shared_group()``. A freshly
    constructed Board holds nothing at all.
    """
    board = Board(MPManager.get_manager())
    assert board._active

    for name, value in vars(board).items():
        assert type(value).__module__ != "multiprocessing.managers", (
            f"Board.{name} is a SyncManager proxy ({type(value)!r}); it must not "
            "be held on the Board or it will be reused across fork()")

    assert board._group is None, \
        "the group member must be built in open_dashboard(), not inherited"


def test_shared_group_proxy_is_rebuilt_after_fork(monkeypatch):
    """An inherited proxy must never be reused from a child process.

    Both ends would then drive the same inherited socket and corrupt the
    manager's framed protocol. The cache is keyed on pid so a child
    transparently builds its own connection.
    """
    first = MPManager.get_shared_group("dashboard")
    assert first is not None
    # Same process and name: cached, so a loop does not pay for a new proxy
    # (and a new connection) on every tick.
    assert MPManager.get_shared_group("dashboard") is first

    real_getpid = os.getpid
    monkeypatch.setattr(os, "getpid", lambda: real_getpid() + 1)
    second = MPManager.get_shared_group("dashboard")
    assert second is not None
    assert second is not first
