import io
import logging
import pytest
import queue
import random
import sys
import threading

from rich.console import Console, Group
from rich.table import Table
from rich.padding import Padding
from rich.progress import Progress

from unittest.mock import patch

from siliconcompiler.report.dashboard.cli import CliDashboard
from siliconcompiler.report.dashboard.cli.board import (
    Board,
    LogBuffer,
    JobData,
    Layout,
    View,
)
from siliconcompiler.report.dashboard.cli.keyboard import Keyboard
from siliconcompiler import NodeStatus
from siliconcompiler.utils.multiprocessing import MPManager


@pytest.fixture
def fake_console(monkeypatch):
    monkeypatch.setattr(Console, "is_terminal", True)


@pytest.fixture(autouse=True)
def reset_singleton(monkeypatch):
    class MockManager:
        def Lock(self):
            return threading.Lock()

        def Event(self):
            return threading.Event()

        def Queue(self):
            return queue.Queue()

        def dict(self):
            return {}

        def Namespace(self):
            class Dummy:
                pass
            return Dummy()

    monkeypatch.setattr(MPManager, "get_dashboard", lambda: Board(MockManager()))


@pytest.fixture
def mock_project(asic_gcd):
    asic_gcd.set('option', 'design', 'test_design')
    asic_gcd.set('option', 'jobname', 'test_job')
    return asic_gcd


@pytest.fixture
def mock_running_job_lg():
    mock_job_data = JobData()
    mock_job_data.total = 30
    mock_job_data.visible = 30
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    statuses = [NodeStatus.SUCCESS, NodeStatus.ERROR, NodeStatus.PENDING]
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": statuses[index % len(statuses)],
            "log": [(f"node{index + 1}.log", f"node{index + 1}.log"),
                    (f"second_node{index + 1}.log", f"second_node{index + 1}.log")],
            "metrics": ["", ""],
            "time": {
                "duration": None,
                "start": None
            },
            "print": {
                "order": (index, index),
                "priority": 0 if statuses[index % len(statuses)] == NodeStatus.ERROR else index,
                "hide": False
            }
        }
        for index in range(mock_job_data.total)
    ]
    mock_job_data.success = sum(1 for node in mock_job_data.nodes
                                if NodeStatus.is_success(node["status"]))
    mock_job_data.error = sum(1 for node in mock_job_data.nodes
                              if NodeStatus.is_error(node["status"]))
    mock_job_data.finished = mock_job_data.success + mock_job_data.error
    return mock_job_data


@pytest.fixture
def mock_running_job_lg_second():
    mock_job_data = JobData()
    mock_job_data.total = 30
    mock_job_data.visible = 30
    mock_job_data.design = "design2"
    mock_job_data.jobname = "job2"
    statuses = [NodeStatus.ERROR, NodeStatus.PENDING, NodeStatus.SUCCESS]
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": statuses[index % len(statuses)],
            "log": [(f"node{index + 1}.log", f"node{index + 1}.log")],
            "metrics": ["", ""],
            "time": {
                "duration": None,
                "start": None
            },
            "print": {
                "order": (index, index),
                "priority": 0 if statuses[index % len(statuses)] == NodeStatus.ERROR else index,
                "hide": False
            }
        }
        for index in range(mock_job_data.total)
    ]
    mock_job_data.success = sum(1 for node in mock_job_data.nodes
                                if NodeStatus.is_success(node["status"]))
    mock_job_data.error = sum(1 for node in mock_job_data.nodes
                              if NodeStatus.is_error(node["status"]))
    mock_job_data.finished = mock_job_data.success + mock_job_data.error
    return mock_job_data


@pytest.fixture
def mock_running_job():
    mock_job_data = JobData()
    mock_job_data.total = 5
    mock_job_data.visible = 5
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    statuses = [NodeStatus.SUCCESS, NodeStatus.ERROR, NodeStatus.PENDING]
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": random.choice(statuses),
            "metrics": ["", ""],
            "log": [(f"node{index + 1}.log", f"node{index + 1}.log")],
            "print": {
                "order": (index, index),
                "priority": 0 if statuses[index % len(statuses)] == NodeStatus.ERROR else index,
                "hide": False
            }
        }
        for index in range(mock_job_data.total)
    ]
    mock_job_data.success = sum(1 for node in mock_job_data.nodes
                                if NodeStatus.is_success(node["status"]))
    mock_job_data.error = sum(1 for node in mock_job_data.nodes
                              if NodeStatus.is_error(node["status"]))
    mock_job_data.finished = mock_job_data.success + mock_job_data.error
    return mock_job_data


@pytest.fixture
def mock_finished_job_fail():
    mock_job_data = JobData()
    mock_job_data.total = 5
    mock_job_data.visible = 5
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    statuses = [NodeStatus.SUCCESS, NodeStatus.ERROR]
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": statuses[index % len(statuses)],
            "metrics": ["", ""],
            "log": [(f"node{index + 1}.log", f"node{index + 1}.log")],
            "time": {
                "duration": 5.0,
                "start": None
            },
            "print": {
                "order": (index, index),
                "priority": 0 if statuses[index % len(statuses)] == NodeStatus.ERROR else index,
                "hide": False
            }
        }
        for index in range(mock_job_data.total)
    ]
    mock_job_data.success = sum(1 for node in mock_job_data.nodes
                                if NodeStatus.is_success(node["status"]))
    mock_job_data.error = sum(1 for node in mock_job_data.nodes
                              if NodeStatus.is_error(node["status"]))
    mock_job_data.finished = mock_job_data.success + mock_job_data.error
    return mock_job_data


@pytest.fixture
def mock_finished_job_passed():
    mock_job_data = JobData()
    mock_job_data.total = 5
    mock_job_data.visible = 5
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": NodeStatus.SUCCESS,
            "metrics": ["", ""],
            "log": [(f"node{index + 1}.log", f"node{index + 1}.log")],
            "time": {
                "duration": 5.0,
                "start": None
            },
            "print": {
                "order": (index, index),
                "priority": index,
                "hide": False
            }
        }
        for index in range(mock_job_data.total)
    ]
    mock_job_data.success = len(mock_job_data.nodes)
    mock_job_data.error = 0
    mock_job_data.finished = mock_job_data.success + mock_job_data.error
    return mock_job_data


@pytest.fixture
def dashboard(mock_project, fake_console):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_project)
        return dashboard


@pytest.fixture
def dashboard_xsmall(mock_project, fake_console):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_project)
        dashboard._dashboard._console.height = 2
        dashboard._dashboard._console.width = 120

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard.set_logger(logger)

        return dashboard


@pytest.fixture
def dashboard_small(mock_project, fake_console):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_project)
        dashboard._dashboard._console.height = 14
        dashboard._dashboard._console.width = 120

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard.set_logger(logger)

        return dashboard


@pytest.fixture
def dashboard_medium(mock_project, fake_console):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_project)
        dashboard._dashboard._console.height = 40
        dashboard._dashboard._console.width = 200

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard.set_logger(logger)

        return dashboard


@pytest.fixture
def dashboard_large(mock_project, fake_console):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_project)
        dashboard._dashboard._console.height = 100
        dashboard._dashboard._console.width = 300

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard.set_logger(logger)

        return dashboard


def test_init(dashboard):
    dashboard = dashboard._dashboard

    assert dashboard._render_data.total == 0
    assert dashboard._render_data.success == 0
    assert dashboard._render_data.error == 0

    assert dashboard._active


def test_no_tty(mock_project, monkeypatch):
    monkeypatch.setattr(Console, "is_terminal", False)

    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_project)

    assert not dashboard._dashboard._active


def test_set_get_logger(dashboard):
    logger = logging.getLogger("test")
    assert dashboard._logger is not logger
    dashboard.set_logger(logger)
    assert dashboard._logger is logger


@pytest.mark.parametrize(
    "status",
    [
        NodeStatus.PENDING,
        NodeStatus.QUEUED,
        NodeStatus.RUNNING,
        NodeStatus.SUCCESS,
        NodeStatus.ERROR,
        NodeStatus.SKIPPED,
        NodeStatus.TIMEOUT,
    ],
)
def test_format_status(status):
    assert f"[node.{status}]{status.upper()}[/]" == Board.format_status(status)


def test_format_status_unknown():
    assert "[node.notarealstatus]NOTAREALSTATUS[/]" in Board.format_status(
        "notarealstatus"
    )


def test_format_node():
    assert Board.format_node("design1", "job1", "step1", 1, False) == "step1/1"
    assert Board.format_node("design1", "job1", "step1", 1, True) == "design1/job1/step1/1"


def test_stop_dashboard(dashboard):
    dashboard = dashboard._dashboard

    assert dashboard._render_thread is None
    dashboard.open_dashboard()
    assert dashboard._render_thread is not None
    dashboard.stop()
    assert dashboard._render_thread is not None
    assert not dashboard.is_running()


def test_log_buffer_handler():
    event = threading.Event()
    buffer = LogBuffer(queue.Queue(), n=2, event=event)

    record1 = logging.LogRecord("test", logging.INFO, "path", 1, "msg1", (), None)
    record2 = logging.LogRecord("test", logging.INFO, "path", 1, "msg2", (), None)

    buffer.make_handler({}).emit(record1)
    buffer.make_handler({}).emit(record2)

    lines = buffer.get_lines()
    assert len(lines) == 2
    assert "msg1" in lines[0]
    assert "msg2" in lines[1]


def test_update_render_data(dashboard, mock_running_job_lg):
    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg

        with dashboard._dashboard._job_data_lock:
            assert len(dashboard._dashboard._job_data) == 0
            assert not dashboard._dashboard._board_info.data_modified

        # Trigger the update
        dashboard.update_manifest()

        dashboard = dashboard._dashboard

        # Verify the total results
        with dashboard._job_data_lock:
            assert len(dashboard._job_data) == 1
            assert dashboard._board_info.data_modified

        dashboard._update_rendable_data()
        with dashboard._job_data_lock:
            assert not dashboard._board_info.data_modified


def test_layout_small_width():
    layout = Layout()
    layout.update(height=2, width=100, visible_jobs=10, visible_bars=1)

    assert layout.job_board_show_log is False


def test_layout_progress_bar_only():
    """When the console is way to small for any job, display only the progress bar"""
    layout = Layout()
    layout.update(height=2, width=300, visible_jobs=10, visible_bars=1)

    assert layout.job_board_height == 0
    assert layout.log_height == 0
    assert layout.progress_bar_height == 2
    assert layout.job_board_show_log is True


def test_layout_truncate_jobs():
    """When the console is not big enough for all the jobs, display the
    progress bar and as many jobs as possible.
    """

    console_height = 10
    layout = Layout()
    layout.update(height=console_height, width=300, visible_jobs=10, visible_bars=1)

    assert layout.job_board_height == 4
    assert layout.log_height == 4
    assert layout.progress_bar_height == 2
    assert layout.job_board_show_log is True


def test_layout_log_fill():
    """On large console that fit all jobs, display job and progress bar,
    then fill the available with the log.
    """
    console_height = 100
    console_width = 300
    visible_jobs = 10
    visible_bars = 1
    layout = Layout()
    layout.update(console_height, console_width, visible_jobs, visible_bars)

    assert layout.job_board_height == 13
    assert layout.progress_bar_height == 2
    assert layout.log_height == 85
    assert layout.job_board_show_log is True


def test_layout_log_fill_lots_of_jobs():
    """On large console that fit all jobs, display job and progress bar,
    then fill the available with the log.
    """
    console_height = 100
    console_width = 300
    visible_jobs = 20
    visible_bars = 1
    layout = Layout()
    layout.update(console_height, console_width, visible_jobs, visible_bars)

    assert layout.job_board_height == 23
    assert layout.progress_bar_height == 2
    assert layout.log_height == 75
    assert layout.job_board_show_log is True


def test_render_log_basic(mock_running_job_lg, dashboard_medium):
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)

    dashboard_medium.set_logger(logger)

    # Basic Test
    logger.log(logging.INFO, "first row")
    logger.log(logging.INFO, "second row")

    log = dashboard._render_log(dashboard._layout)
    assert isinstance(log, Table)
    assert log.row_count == 19

    # Capture the output
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    console.print(log)

    consoleprint = io_file.getvalue().splitlines()
    assert len(consoleprint) == 19
    assert consoleprint[0].rstrip() == "\x1b[37m| INFO     | first row\x1b[0m"
    assert consoleprint[1].rstrip() == "\x1b[37m| INFO     | second row\x1b[0m"
    for n in range(2, 19):
        assert consoleprint[n].strip() == ""  # padding


def test_render_log_basic_eol(mock_running_job_lg, dashboard_medium):
    dashboard = dashboard_medium._dashboard
    dashboard._console.width = 20
    if sys.platform == "win32":
        dashboard._console.width += 2  # Adjust for Windows extra character in line endings

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)

    dashboard_medium.set_logger(logger)

    # Basic Test
    logger.log(logging.INFO, "first row")
    logger.log(logging.INFO, "second row")

    log = dashboard._render_log(dashboard._layout)
    assert isinstance(log, Table)
    assert log.row_count == 19

    # Capture the output
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    console.print(log)

    consoleprint = io_file.getvalue().splitlines()
    assert len(consoleprint) == 19
    assert consoleprint[0].rstrip() == \
        "\x1b[37m| INFO     | first …\x1b[0m"  # codespell:ignore firs
    assert consoleprint[1].rstrip() == \
        "\x1b[37m| INFO     | second…\x1b[0m"  # codespell:ignore seco
    for n in range(2, 19):
        assert consoleprint[n].strip() == ""  # padding


def test_render_log_truncate(mock_running_job_lg, dashboard_medium):
    """Test that it truncates all but the last 10 lines"""
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_layout()

    dashboard._layout.log_height = 11
    assert dashboard._layout.log_height == 11
    assert dashboard._layout.job_board_height == 0
    assert dashboard._layout.progress_bar_height == 0

    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)

    dashboard_medium.set_logger(logger)

    for i in range(0, 200):
        logger.log(logging.INFO, f"log row {i}")

    log = dashboard._render_log(dashboard._layout)
    assert isinstance(log, Table)

    assert log.row_count == 11

    # Check content
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    console.print(log)
    actual_output = console.file.getvalue()
    actual_lines = actual_output.splitlines(keepends=True)
    start_index = 200 - 11
    for i, line in enumerate(actual_lines):
        if start_index + i == 200:
            assert len(line.strip()) == 0
        else:
            assert f"log row {start_index + i}" in line


def test_render_log_only(mock_running_job_lg, dashboard_medium):
    dashboard = dashboard_medium._dashboard
    dashboard._layout.show_jobboard = False
    dashboard._layout.show_progress_bar = False
    dashboard._layout.show_log = True

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_layout()

    assert dashboard._layout.log_height == 40
    assert dashboard._layout.job_board_height == 0
    assert dashboard._layout.progress_bar_height == 0

    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)

    dashboard_medium.set_logger(logger)

    for i in range(0, 200):
        logger.log(logging.INFO, f"log row {i}")

    log = dashboard._render_log(dashboard._layout)
    assert isinstance(log, Table)

    assert log.row_count == 40

    # Check content
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    console.print(log)
    actual_output = console.file.getvalue()
    actual_lines = actual_output.splitlines(keepends=True)
    start_index = 200 - 40
    for i, line in enumerate(actual_lines):
        if start_index + i == 200:
            assert len(line.strip()) == 0
        else:
            assert f"log row {start_index + i}" in line


def test_render_job_dashboard(mock_running_job_lg, dashboard_medium):
    """Test that the job dashboard is created properly"""
    dashboard = dashboard_medium._dashboard

    for n in range(1, mock_running_job_lg.total+1):
        if n % 2 == 0:
            with open(f"node{n}.log", "w") as f:
                f.write("test")

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    job_board = dashboard._render_job_dashboard(dashboard._layout)

    assert isinstance(job_board, Group)

    assert len(job_board.renderables) == 2

    job_table = job_board.renderables[0]
    assert isinstance(job_table, Table)

    assert job_table.row_count == 16

    # Check the content
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    console.print(job_table)

    # Remove all white spaces
    actual_output = console.file.getvalue()
    actual_lines = [
        line.translate(str.maketrans("", "", " \t\n\r\f\v"))
        for line in actual_output.splitlines()
    ]

    expected_lines_all = []
    for n, node in enumerate(mock_running_job_lg.nodes, start=1):
        if node["status"] in [NodeStatus.SKIPPED]:
            continue
        if n % 2 == 0:
            log = f'\x1b[90m{node["log"][0][0]}\x1b[0m'
        else:
            log = ""
        status = node["status"].upper()
        job_id = "/".join(
            [
                node["step"],
                str(node["index"]),
            ]
        )
        div = ""
        expected_line = f"{status}{div}{job_id}{div}{div}{div}{div}{log}".translate(
            str.maketrans("", "", " \t\n\r\f\v"))
        expected_lines_all.append(expected_line)

    actual_lines = actual_lines[2:]
    assert len(actual_lines) == 16

    expected_lines = [
        expected_lines_all[0],
        expected_lines_all[1],
        expected_lines_all[2],
        expected_lines_all[3],
        expected_lines_all[4],
        expected_lines_all[5],
        expected_lines_all[6],
        expected_lines_all[7],
        expected_lines_all[8],
        expected_lines_all[10],
        expected_lines_all[13],
        expected_lines_all[16],
        expected_lines_all[19],
        expected_lines_all[22],
        expected_lines_all[25],
        expected_lines_all[28]
    ]
    assert len(actual_lines) == len(expected_lines)
    for i, (actual, expected) in enumerate(zip(actual_lines, expected_lines)):
        assert actual == expected, f"line {i} does not match"


def test_render_job_dashboard_hide_before_from(mock_running_job_lg, dashboard_medium):
    """Test that the job dashboard is created properly"""
    dashboard = dashboard_medium._dashboard

    for n in range(0, mock_running_job_lg.total):
        if n % 2 == 0:
            # Hide every other node
            mock_running_job_lg.nodes[n]["print"]["hide"] = True

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    job_board = dashboard._render_job_dashboard(dashboard._layout)

    assert isinstance(job_board, Group)

    assert len(job_board.renderables) == 2

    job_table = job_board.renderables[0]
    assert isinstance(job_table, Table)

    assert job_table.row_count == 15

    # Check the content
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    console.print(job_table)

    # Remove all white spaces
    actual_output = console.file.getvalue()
    actual_lines = [
        line.translate(str.maketrans("", "", " \t\n\r\f\v"))
        for line in actual_output.splitlines()
    ]

    expected_lines_all = []
    for node in mock_running_job_lg.nodes:
        if node["status"] in [NodeStatus.SKIPPED] or node["print"]["hide"]:
            continue
        log = ""
        status = node["status"].upper()
        job_id = "/".join(
            [
                node["step"],
                str(node["index"]),
            ]
        )
        div = ""
        expected_line = f"{status}{div}{job_id}{div}{div}{div}{div}{log}".translate(
            str.maketrans("", "", " \t\n\r\f\v"))
        expected_lines_all.append(expected_line)

    actual_lines = actual_lines[2:]
    assert len(actual_lines) == 15

    assert len(actual_lines) == len(expected_lines_all)
    for i, (actual, expected) in enumerate(zip(actual_lines, expected_lines_all)):
        assert actual == expected, f"line {i} does not match {actual} != {expected}"


def test_render_job_dashboard_select_logs(mock_running_job_lg, dashboard_medium):
    """Test that the job dashboard is created properly"""
    dashboard = dashboard_medium._dashboard

    for n in range(1, mock_running_job_lg.total+1):
        if n % 2 == 0:
            with open(f"node{n}.log", "w"):
                pass
            with open(f"second_node{n}.log", "w") as f:
                f.write("test")

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    job_board = dashboard._render_job_dashboard(dashboard._layout)

    assert isinstance(job_board, Group)

    assert len(job_board.renderables) == 2

    job_table = job_board.renderables[0]
    assert isinstance(job_table, Table)

    assert job_table.row_count == 16

    # Check the content
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    console.print(job_table)

    # Remove all white spaces
    actual_output = console.file.getvalue()
    actual_lines = [
        line.translate(str.maketrans("", "", " \t\n\r\f\v"))
        for line in actual_output.splitlines()
    ]

    expected_lines_all = []
    for n, node in enumerate(mock_running_job_lg.nodes, start=1):
        if node["status"] in [NodeStatus.SKIPPED]:
            continue
        if n % 2 == 0:
            log = f'\x1b[90m{node["log"][1][0]}\x1b[0m'
        else:
            log = ""
        status = node["status"].upper()
        job_id = "/".join(
            [
                node["step"],
                str(node["index"]),
            ]
        )
        div = ""
        expected_line = f"{status}{div}{job_id}{div}{div}{div}{div}{log}".translate(
            str.maketrans("", "", " \t\n\r\f\v"))
        expected_lines_all.append(expected_line)

    actual_lines = actual_lines[2:]
    assert len(actual_lines) == 16

    expected_lines = [
        expected_lines_all[0],
        expected_lines_all[1],
        expected_lines_all[2],
        expected_lines_all[3],
        expected_lines_all[4],
        expected_lines_all[5],
        expected_lines_all[6],
        expected_lines_all[7],
        expected_lines_all[8],
        expected_lines_all[10],
        expected_lines_all[13],
        expected_lines_all[16],
        expected_lines_all[19],
        expected_lines_all[22],
        expected_lines_all[25],
        expected_lines_all[28]
    ]
    assert len(actual_lines) == len(expected_lines)
    for i, (actual, expected) in enumerate(zip(actual_lines, expected_lines)):
        assert actual == expected, f"line {i} does not match"


def test_render_job_dashboard_select_no_logs(mock_running_job_lg, dashboard_medium):
    """Test that the job dashboard is created properly"""
    dashboard = dashboard_medium._dashboard

    for n in range(1, mock_running_job_lg.total+1):
        if n % 2 == 0:
            with open(f"node{n}.log", "w"):
                pass
            with open(f"second_node{n}.log", "w"):
                pass

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    job_board = dashboard._render_job_dashboard(dashboard._layout)

    assert isinstance(job_board, Group)

    assert len(job_board.renderables) == 2

    job_table = job_board.renderables[0]
    assert isinstance(job_table, Table)

    assert job_table.row_count == 16

    # Check the content
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    console.print(job_table)

    # Remove all white spaces
    actual_output = console.file.getvalue()
    actual_lines = [
        line.translate(str.maketrans("", "", " \t\n\r\f\v"))
        for line in actual_output.splitlines()
    ]

    expected_lines_all = []
    for n, node in enumerate(mock_running_job_lg.nodes, start=1):
        if node["status"] in [NodeStatus.SKIPPED]:
            continue
        log = ""
        status = node["status"].upper()
        job_id = "/".join(
            [
                node["step"],
                str(node["index"]),
            ]
        )
        div = ""
        expected_line = f"{status}{div}{job_id}{div}{div}{div}{div}{log}".translate(
            str.maketrans("", "", " \t\n\r\f\v"))
        expected_lines_all.append(expected_line)

    actual_lines = actual_lines[2:]
    assert len(actual_lines) == 16

    expected_lines = [
        expected_lines_all[0],
        expected_lines_all[1],
        expected_lines_all[2],
        expected_lines_all[3],
        expected_lines_all[4],
        expected_lines_all[5],
        expected_lines_all[6],
        expected_lines_all[7],
        expected_lines_all[8],
        expected_lines_all[10],
        expected_lines_all[13],
        expected_lines_all[16],
        expected_lines_all[19],
        expected_lines_all[22],
        expected_lines_all[25],
        expected_lines_all[28]
    ]
    assert len(actual_lines) == len(expected_lines)
    for i, (actual, expected) in enumerate(zip(actual_lines, expected_lines)):
        assert actual == expected, f"line {i} does not match"


def test_render_job_dashboard_multi_job(mock_running_job_lg, mock_running_job_lg_second,
                                        dashboard_medium):
    """Test that the job dashboard is created properly"""
    dashboard = dashboard_medium._dashboard

    for n in range(1, mock_running_job_lg.total+1):
        if n % 2 == 0:
            with open(f"node{n}.log", "w") as f:
                f.write("test")

    for n in range(1, mock_running_job_lg_second.total+1):
        if n % 2 == 0:
            with open(f"node{n}.log", "w") as f:
                f.write("test")

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._project)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg_second
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    assert dashboard._layout.job_board_height == 18
    assert dashboard._layout.progress_bar_height == 3
    assert dashboard._layout.log_height == 19

    job_board = dashboard._render_job_dashboard(dashboard._layout)

    assert isinstance(job_board, Group)

    assert len(job_board.renderables) == 2

    job_table = job_board.renderables[0]
    assert isinstance(job_table, Table)

    assert job_table.row_count == 15

    # Check the content
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    console.print(job_table)

    # Remove all white spaces
    actual_output = console.file.getvalue()
    actual_lines = [
        line.translate(str.maketrans("", "", " \t\n\r\f\v"))
        for line in actual_output.splitlines()
    ]

    expected_lines_all_job1 = []
    for n, node in enumerate(mock_running_job_lg.nodes, start=1):
        if node["status"] in [NodeStatus.SKIPPED]:
            continue
        if n % 2 == 0:
            log = f'\x1b[90m{node["log"][0][0]}\x1b[0m'
        else:
            log = ""
        status = node["status"].upper()
        job_id = "/".join(
            [
                mock_running_job_lg.design,
                mock_running_job_lg.jobname,
                node["step"],
                str(node["index"]),
            ]
        )
        div = ""
        expected_line = f"{status}{div}{job_id}{div}{div}{div}{div}{log}".translate(
            str.maketrans("", "", " \t\n\r\f\v"))
        expected_lines_all_job1.append(expected_line)

    expected_lines_all_job2 = []
    for n, node in enumerate(mock_running_job_lg_second.nodes, start=1):
        if node["status"] in [NodeStatus.SKIPPED]:
            continue
        if n % 2 == 0:
            log = f'\x1b[90m{node["log"][0][0]}\x1b[0m'
        else:
            log = ""
        status = node["status"].upper()
        job_id = "/".join(
            [
                mock_running_job_lg_second.design,
                mock_running_job_lg_second.jobname,
                node["step"],
                str(node["index"]),
            ]
        )
        div = ""
        expected_line = f"{status}{div}{job_id}{div}{div}{div}{div}{log}".translate(
            str.maketrans("", "", " \t\n\r\f\v"))
        expected_lines_all_job2.append(expected_line)

    actual_lines = actual_lines[2:]
    assert len(actual_lines) == 15  # Layout changes may reduce line count

    expected_lines = [
        expected_lines_all_job1[0],
        expected_lines_all_job1[1],
        expected_lines_all_job1[4],
        expected_lines_all_job1[7],
        expected_lines_all_job1[10],
        expected_lines_all_job1[13],
        expected_lines_all_job1[16],
        expected_lines_all_job1[19],
        expected_lines_all_job2[0],
        expected_lines_all_job2[3],
        expected_lines_all_job2[6],
        expected_lines_all_job2[9],
        expected_lines_all_job2[12],
        expected_lines_all_job2[15],
        expected_lines_all_job2[18]
    ]
    assert len(actual_lines) == len(expected_lines)
    for i, (actual, expected) in enumerate(zip(actual_lines, expected_lines)):
        assert actual == expected, f"line {i} does not match"


def test_render_job_dashboard_multi_job_limit_progress(
        mock_running_job_lg, mock_running_job_lg_second,
        dashboard_xsmall):
    """Test that the job dashboard is created properly"""
    dashboard = dashboard_xsmall._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_xsmall._project)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg_second
        dashboard._update_render_data(dashboard_xsmall._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    assert dashboard._layout.job_board_height == 0
    # Ensure to show just one job
    assert dashboard._layout.progress_bar_height == 2
    assert dashboard._layout.log_height == 0

    progress_bars = dashboard._render_progress_bar(dashboard._layout)

    assert isinstance(progress_bars, Group)
    assert len(progress_bars.renderables) == 2

    progress = progress_bars.renderables[0]
    assert isinstance(progress, Progress)
    assert len(progress._tasks) == 1


def test_get_rendable_xsmall_dashboard_running(mock_running_job_lg, dashboard_xsmall):
    """Test that on xtra small dashboard display only the progress bar."""
    dashboard = dashboard_xsmall._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard_xsmall.set_logger(None)
        dashboard._update_render_data(dashboard_xsmall._project)

    dashboard._update_rendable_data()
    rendable = dashboard._get_rendable()

    assert isinstance(rendable, Group)
    assert len(rendable.renderables) == 1

    # Verify the order
    progress = rendable.renderables[0]

    assert isinstance(progress, Group)

    assert len(progress.renderables) == 2
    assert isinstance(progress.renderables[0], Progress)
    assert isinstance(progress.renderables[1], Padding)

    progress.renderables[0]


def test_get_rendable_small_dashboard_running(mock_running_job_lg, dashboard_small):
    """On smaller dashboards that barely fit the jobs, don't display the log"""
    dashboard = dashboard_small._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard_small.set_logger(None)
        dashboard._update_render_data(dashboard_small._project)

    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    dashboard_small.set_logger(logger)

    for i in range(100):
        logger.log(logging.INFO, f"{i}th row")

    dashboard._update_rendable_data()
    rendable = dashboard._get_rendable()

    assert isinstance(rendable, Group)
    assert len(rendable.renderables) == 3

    job_board = rendable.renderables[0]
    assert isinstance(job_board, Group)
    assert len(job_board.renderables) == 2
    assert isinstance(job_board.renderables[0], Table)
    assert isinstance(job_board.renderables[1], Padding)
    assert job_board.renderables[0].row_count == 3

    progress = rendable.renderables[1]
    assert isinstance(progress, Group)
    assert len(progress.renderables) == 2
    assert isinstance(progress.renderables[0], Progress)
    assert isinstance(progress.renderables[1], Padding)

    log = rendable.renderables[2]
    assert isinstance(log, Table)
    assert log.row_count == 6


def test_get_rendable_medium_dashboard_running(mock_running_job_lg, dashboard_medium):
    """On medium and large dashboards display everything, with proper padding."""
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard_medium.set_logger(None)
        dashboard._update_render_data(dashboard_medium._project)

    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    dashboard_medium.set_logger(logger)

    for i in range(100):
        logger.log(logging.INFO, f"{i}th row")

    dashboard._update_rendable_data()
    rendable = dashboard._get_rendable()

    assert isinstance(rendable, Group)
    assert len(rendable.renderables) == 3

    # Verify the order
    job_board = rendable.renderables[0]
    progress = rendable.renderables[1]
    log = rendable.renderables[2]

    assert isinstance(job_board, Group)
    assert len(job_board.renderables) == 2
    assert isinstance(job_board.renderables[0], Table)
    assert isinstance(job_board.renderables[1], Padding)
    assert job_board.renderables[0].row_count == 16

    assert isinstance(progress, Group)
    assert len(progress.renderables) == 2
    assert isinstance(progress.renderables[0], Progress)
    assert isinstance(progress.renderables[1], Padding)

    assert isinstance(log, Table)
    assert log.row_count == 19


def test_get_rendable_xsmall_dashboard_finished_success(mock_finished_job_passed, dashboard_xsmall):
    dashboard = dashboard_xsmall._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_passed
        dashboard._update_render_data(dashboard_xsmall._project)

    dashboard._update_rendable_data()
    rendable = dashboard._get_rendable()

    assert isinstance(rendable, Group)
    assert len(rendable.renderables) == 1

    # Display Summary
    assert isinstance(rendable.renderables[0], Group)


def test_get_rendable_small_dashboard_finished_success(mock_finished_job_passed, dashboard_small):
    dashboard = dashboard_small._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_passed
        dashboard._update_render_data(dashboard_small._project)

    dashboard._update_rendable_data()
    rendable = dashboard._get_rendable()

    assert isinstance(rendable, Group)
    assert len(rendable.renderables) == 3

    jobs = rendable.renderables[0]
    assert isinstance(jobs, Group)
    assert len(jobs.renderables) == 2
    assert isinstance(jobs.renderables[0], Table)
    assert isinstance(jobs.renderables[1], Padding)

    # Display Log
    assert isinstance(rendable.renderables[1], Group)
    assert isinstance(rendable.renderables[2], Table)


def test_get_rendable_medium_dashboard_finished_success(mock_finished_job_passed, dashboard_medium):
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_passed
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    rendable = dashboard._get_rendable()

    assert isinstance(rendable, Group)
    assert len(rendable.renderables) == 3

    jobs = rendable.renderables[0]
    assert isinstance(jobs, Group)
    assert len(jobs.renderables) == 2
    assert isinstance(jobs.renderables[0], Table)
    assert isinstance(jobs.renderables[1], Padding)

    # Display Log
    assert isinstance(rendable.renderables[1], Group)
    assert isinstance(rendable.renderables[2], Table)


def test_get_rendable_xsmall_dashboard_finished_fail(mock_finished_job_fail, dashboard_xsmall):
    dashboard = dashboard_xsmall._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_fail
        dashboard._update_render_data(dashboard_xsmall._project)

    dashboard._update_rendable_data()
    rendable = dashboard._get_rendable()

    assert isinstance(rendable, Group)
    assert len(rendable.renderables) == 1

    # Display Done
    progress = rendable.renderables[0]
    assert len(progress.renderables) == 2
    assert isinstance(progress.renderables[0], Progress)
    assert isinstance(progress.renderables[1], Padding)


def test_layout_limit_jobs():
    layout = Layout()

    layout.update(15, 120, 50, 20)
    assert layout.job_board_height == 3
    assert layout.progress_bar_height == 9
    assert layout.log_height == 3


def test_layout_1to1_jobs():
    layout = Layout()

    layout.update(40, 120, 20, 20)
    assert layout.job_board_height == 9
    assert layout.progress_bar_height == 21
    assert layout.log_height == 10


def test_layout_normal_size():
    layout = Layout()

    layout.update(50, 120, 15, 5)
    assert layout.job_board_height == 18
    assert layout.progress_bar_height == 6
    assert layout.log_height == 26


def test_get_job(mock_project, fake_console):
    dashboard = MPManager.get_dashboard()

    job = dashboard._get_job(mock_project)
    assert isinstance(job, JobData)

    assert job.total == 19
    assert job.error == 0
    assert job.success == 0
    assert job.skipped == 0
    assert job.finished == 0
    assert job.design == "test_design"
    assert job.complete is False
    assert len(job.nodes) == 19


def test_get_job_with_skipped(mock_project, fake_console):
    mock_project.set("record", "status", "skipped", step="route.detailed", index=0)

    dashboard = MPManager.get_dashboard()

    job = dashboard._get_job(mock_project)
    assert isinstance(job, JobData)

    assert job.total == 19
    assert job.error == 0
    assert job.success == 1
    assert job.skipped == 1
    assert job.finished == 1
    assert job.design == "test_design"
    assert job.complete is False
    assert len(job.nodes) == 18


def test_get_job_with_status(mock_project, fake_console):
    mock_project.set("record", "status", "success", step="route.global", index=0)
    mock_project.set("record", "status", "skipped", step="route.detailed", index=0)
    mock_project.set("record", "status", "error", step="write.views", index=0)

    dashboard = MPManager.get_dashboard()

    job = dashboard._get_job(mock_project)
    assert isinstance(job, JobData)

    assert job.total == 19
    assert job.error == 1
    assert job.success == 2
    assert job.skipped == 1
    assert job.finished == 3
    assert job.design == "test_design"
    assert job.complete is False
    assert len(job.nodes) == 18


def test_render_help_full_height(mock_project, fake_console):
    """Test rendering help display with full height (banner, authors, version, table)"""
    dashboard = MPManager.get_dashboard()

    layout = Layout()
    layout.height = 50  # Enough for all sections

    help_group = dashboard._render_help(layout)

    assert isinstance(help_group, list)
    # Should have banner, authors, version, and table
    assert len(help_group) == 4
    assert isinstance(help_group[0], Padding)  # Banner
    assert isinstance(help_group[1], Padding)  # Authors
    assert isinstance(help_group[2], Padding)  # Version
    assert isinstance(help_group[3], Table)   # Help table


def test_render_help_medium_height(mock_project, fake_console):
    """Test rendering help display with medium height (banner, authors, table)"""
    dashboard = MPManager.get_dashboard()

    layout = Layout()
    layout.height = 21  # Enough for banner, authors, and table but not version

    help_group = dashboard._render_help(layout)

    assert isinstance(help_group, list)
    # Should have banner, authors, and table (no version)
    assert len(help_group) == 3
    assert isinstance(help_group[0], Padding)  # Banner
    assert isinstance(help_group[1], Padding)  # Authors
    assert isinstance(help_group[2], Table)   # Help table


def test_render_help_small_height(mock_project, fake_console):
    """Test rendering help display with small height (banner and table only)"""
    dashboard = MPManager.get_dashboard()

    layout = Layout()
    layout.height = 19  # Enough for banner and table only

    help_group = dashboard._render_help(layout)

    assert isinstance(help_group, list)
    # Should have banner and table only
    assert len(help_group) == 2
    assert isinstance(help_group[0], Padding)  # Banner
    assert isinstance(help_group[1], Table)   # Help table


def test_render_help_minimal_height(mock_project, fake_console):
    """Test rendering help display with minimal height (table only)"""
    dashboard = MPManager.get_dashboard()

    layout = Layout()
    layout.height = 12  # Only enough for table

    help_group = dashboard._render_help(layout)

    assert isinstance(help_group, list)
    # Should have table only
    assert len(help_group) == 1
    assert isinstance(help_group[0], Table)   # Help table


def test_render_help_table_content(mock_project, fake_console):
    """Test that help table contains expected key bindings"""
    dashboard = MPManager.get_dashboard()

    layout = Layout()
    layout.height = 50

    help_group = dashboard._render_help(layout)
    table = help_group[3]  # Last element is the table

    # Check table has correct structure
    assert table.title == "Dashboard Help"
    assert len(table.columns) == 2
    assert table.row_count == 4  # Should have 4 key bindings

    # Verify table content by rendering it
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    console.print(table)
    output = io_file.getvalue()

    # Check for expected key bindings
    assert "h" in output
    assert "Toggle showing this help information" in output
    assert "j" in output
    assert "Toggle showing job details" in output
    assert "n" in output
    assert "Toggle showing node details" in output
    assert "l" in output
    assert "Toggle showing log details" in output


def test_handle_keyboard_toggle_help(mock_project, fake_console):
    """Test keyboard handler toggles help view on 'h' key"""
    dashboard = MPManager.get_dashboard()

    assert dashboard._Board__view == View.NORMAL

    with patch.object(Keyboard, "check_key", return_value="h"):
        dashboard._handle_keyboard()

    assert dashboard._Board__view == View.HELP

    with patch.object(Keyboard, "check_key", return_value="h"):
        dashboard._handle_keyboard()

    assert dashboard._Board__view == View.NORMAL


def test_handle_keyboard_toggle_help_uppercase(mock_project, fake_console):
    """Test keyboard handler handles uppercase 'H' key"""
    dashboard = MPManager.get_dashboard()

    assert dashboard._Board__view == View.NORMAL

    with patch.object(Keyboard, "check_key", return_value="H"):
        dashboard._handle_keyboard()

    assert dashboard._Board__view == View.HELP


def test_handle_keyboard_toggle_progress_bar(mock_project, fake_console):
    """Test keyboard handler toggles progress bar on 'j' key"""
    dashboard = MPManager.get_dashboard()

    initial_state = dashboard._layout.show_progress_bar

    with patch.object(Keyboard, "check_key", return_value="j"):
        dashboard._handle_keyboard()

    assert dashboard._layout.show_progress_bar != initial_state


def test_handle_keyboard_toggle_log(mock_project, fake_console):
    """Test keyboard handler toggles log on 'l' key"""
    dashboard = MPManager.get_dashboard()

    initial_state = dashboard._layout.show_log

    with patch.object(Keyboard, "check_key", return_value="l"):
        dashboard._handle_keyboard()

    assert dashboard._layout.show_log != initial_state


def test_handle_keyboard_toggle_jobboard(mock_project, fake_console):
    """Test keyboard handler toggles jobboard on 'n' key"""
    dashboard = MPManager.get_dashboard()

    initial_state = dashboard._layout.show_jobboard

    with patch.object(Keyboard, "check_key", return_value="n"):
        dashboard._handle_keyboard()

    assert dashboard._layout.show_jobboard != initial_state


def test_handle_keyboard_no_key(mock_project, fake_console):
    """Test keyboard handler does nothing when no key is pressed"""
    dashboard = MPManager.get_dashboard()

    initial_view = dashboard._Board__view
    initial_progress = dashboard._layout.show_progress_bar
    initial_log = dashboard._layout.show_log
    initial_jobboard = dashboard._layout.show_jobboard

    with patch.object(Keyboard, "check_key", return_value=None):
        dashboard._handle_keyboard()

    # Nothing should change
    assert dashboard._Board__view == initial_view
    assert dashboard._layout.show_progress_bar == initial_progress
    assert dashboard._layout.show_log == initial_log
    assert dashboard._layout.show_jobboard == initial_jobboard


def test_handle_keyboard_unknown_key(mock_project, fake_console):
    """Test keyboard handler ignores unknown keys"""
    dashboard = MPManager.get_dashboard()

    initial_view = dashboard._Board__view
    initial_progress = dashboard._layout.show_progress_bar
    initial_log = dashboard._layout.show_log
    initial_jobboard = dashboard._layout.show_jobboard

    with patch.object(Keyboard, "check_key", return_value="x"):
        dashboard._handle_keyboard()

    # Nothing should change
    assert dashboard._Board__view == initial_view
    assert dashboard._layout.show_progress_bar == initial_progress
    assert dashboard._layout.show_log == initial_log
    assert dashboard._layout.show_jobboard == initial_jobboard


def test_get_rendable_help_view(mock_project, mock_running_job_lg, dashboard_medium):
    """Test that _get_rendable returns help when view is HELP"""
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(mock_project)

    dashboard._update_rendable_data()

    # Set view to HELP
    dashboard._Board__view = View.HELP

    rendable = dashboard._get_rendable()

    # Should return help display
    assert isinstance(rendable, Group)
    # Help display has at least the table
    assert len(rendable.renderables) >= 1
    assert isinstance(rendable.renderables[-1], Table)  # Last element should be help table

    # Verify it's actually help by checking table title
    assert rendable.renderables[-1].title == "Dashboard Help"


def test_log_buffer_get_lines_with_limit():
    """Test LogBuffer.get_lines with a specific line limit"""
    event = threading.Event()
    buffer = LogBuffer(queue.Queue(), n=10, event=event)

    # Add more lines than the limit
    for i in range(15):
        buffer.add_line(f"line {i}")

    # Get only last 5 lines
    lines = buffer.get_lines(lines=5)
    assert len(lines) == 5
    assert "line 14" in lines[-1]


def test_log_buffer_get_lines_all():
    """Test LogBuffer.get_lines returns all lines when no limit specified"""
    event = threading.Event()
    buffer = LogBuffer(queue.Queue(), n=10, event=event)

    for i in range(8):
        buffer.add_line(f"line {i}")

    # Get all lines
    lines = buffer.get_lines()
    assert len(lines) == 8


def test_log_buffer_queue_not_empty():
    """Test LogBuffer handles non-empty queue after get_lines"""
    event = threading.Event()
    buffer = LogBuffer(queue.Queue(), n=10, event=event)

    # Add lines
    buffer.add_line("line 1")

    # Get lines but don't exhaust queue
    buffer.queue.put("line 2")
    buffer.get_lines()

    # Event should still be set since queue isn't empty
    assert event.is_set()


def test_render_log_zero_height(mock_running_job_lg, dashboard_medium):
    """Test _render_log returns None when log_height is 0"""
    dashboard = dashboard_medium._dashboard

    layout = Layout()
    layout.log_height = 0

    result = dashboard._render_log(layout)
    assert result is None


def test_render_job_dashboard_zero_height(mock_project, mock_running_job_lg, dashboard_medium):
    """Test _render_job_dashboard returns None when job_board_height is 0"""
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(mock_project)

    dashboard._update_rendable_data()

    layout = Layout()
    layout.job_board_height = 0

    result = dashboard._render_job_dashboard(layout)
    assert result is None


def test_render_job_dashboard_no_nodes(mock_project, dashboard_medium):
    """Test _render_job_dashboard returns None when there are no nodes"""
    dashboard = dashboard_medium._dashboard

    # Empty job data
    empty_job = JobData()
    empty_job.total = 0
    empty_job.visible = 0
    empty_job.nodes = []

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = empty_job
        dashboard._update_render_data(mock_project)

    dashboard._update_rendable_data()

    layout = Layout()
    layout.job_board_height = 10

    result = dashboard._render_job_dashboard(layout)
    assert result is None


def test_update_rendable_data_no_jobs(mock_project, fake_console):
    """Test _update_rendable_data returns early when no jobs"""
    dashboard = MPManager.get_dashboard()

    # Set data_modified to False so no jobs are copied
    dashboard._board_info.data_modified = False

    dashboard._update_rendable_data()

    # Should have no jobs in render data
    assert len(dashboard._render_data.jobs) == 0
