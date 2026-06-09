import io
import logging
import pytest
import queue
import sys
import threading
import time

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
from siliconcompiler import Project, Design, Flowgraph, Task
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.utils.multiprocessing import MPManager


class FauxTask(Task):
    def tool(self):
        return "faux_tool"

    def task(self):
        return "faux_task"


def _project_with_flow():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_file("top.v")

    proj = Project(design)

    flow = Flowgraph("testflow")
    flow.node("faux", FauxTask())
    proj.set_flow(flow)

    return proj


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
                "start": None,
                "totaltime": None
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
                "start": None,
                "totaltime": None
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
                "start": None,
                "totaltime": 5.0
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
                "start": None,
                "totaltime": 5.0
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


def _make_progress_job(nodes, design="design1", jobname="job1", complete=False):
    """Build a minimal JobData suitable for _render_progress_bar tests.

    Each node entry is a (status, duration, start, totaltime) tuple.
    """
    job = JobData()
    job.design = design
    job.jobname = jobname
    job.total = len(nodes)
    job.visible = len(nodes)
    job.complete = complete
    job.nodes = []
    for index, (status, duration, start, totaltime) in enumerate(nodes):
        job.nodes.append({
            "step": f"node{index}",
            "index": index,
            "status": status,
            "metrics": ["", ""],
            "log": [],
            "time": {
                "duration": duration,
                "start": start,
                "totaltime": totaltime,
            },
            "print": {"order": (index, index), "priority": index, "hide": False},
        })
    job.success = sum(1 for n in job.nodes if NodeStatus.is_success(n["status"]))
    job.error = sum(1 for n in job.nodes if NodeStatus.is_error(n["status"]))
    job.finished = job.success + job.error
    return job


def _runtime_strings(progress):
    """Extract the formatted runtime fields from each task in a Progress object.

    Returns a list of (walltime, cputime) tuples; cputime is "" when no
    parallelism was detected (no separate CPU column shown).
    """
    return [(task.fields["walltime"], task.fields["cputime"])
            for task in progress._tasks.values()]


def test_progress_bar_runtime_serial_shows_single_value(dashboard_medium):
    """Serial (non-parallel) runs should display only the total time."""
    dashboard = dashboard_medium._dashboard
    job = _make_progress_job([
        (NodeStatus.SUCCESS, 5.0, None, 5.0),
        (NodeStatus.SUCCESS, 5.0, None, 10.0),
        (NodeStatus.SUCCESS, 5.0, None, 15.0),
    ], complete=True)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project, complete=True)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    rendered = dashboard._render_progress_bar(dashboard._layout)
    runtimes = _runtime_strings(rendered.renderables[0])

    # total = 15, wall = max(totaltime) = 15 -> identical, no parallelism
    assert runtimes == [("0:15.0", "")]


def test_progress_bar_runtime_parallel_completed_shows_total_and_wall(dashboard_medium):
    """A completed parallel job should display total / wall when they differ."""
    dashboard = dashboard_medium._dashboard
    # 3 nodes, each ran 10s but in parallel: totaltime metric is the wall checkpoint
    job = _make_progress_job([
        (NodeStatus.SUCCESS, 10.0, None, 10.0),
        (NodeStatus.SUCCESS, 10.0, None, 10.0),
        (NodeStatus.SUCCESS, 10.0, None, 10.0),
    ], complete=True)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project, complete=True)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    rendered = dashboard._render_progress_bar(dashboard._layout)
    runtimes = _runtime_strings(rendered.renderables[0])

    # wall = 10 (max totaltime metric), total = 30 (sum of work)
    assert runtimes == [("0:10.0", "0:30.0")]


def test_progress_bar_runtime_in_progress_with_running_node(dashboard_medium):
    """In-progress jobs combine done totaltime baseline with active elapsed time."""
    dashboard = dashboard_medium._dashboard
    now = time.time()
    # 2 done nodes (sequential, each 5s) plus 1 running started 3s ago
    job = _make_progress_job([
        (NodeStatus.SUCCESS, 5.0, None, 5.0),
        (NodeStatus.SUCCESS, 5.0, None, 10.0),
        (NodeStatus.RUNNING, None, now - 3.0, None),
    ], complete=False)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    with patch("siliconcompiler.report.dashboard.cli.board.time.time", return_value=now):
        rendered = dashboard._render_progress_bar(dashboard._layout)

    runtimes = _runtime_strings(rendered.renderables[0])

    # total = 5 + 5 + 3 = 13, wall = max(5,10) + 3 = 13 -> no parallelism
    assert runtimes == [("0:13.0", "")]


def test_progress_bar_runtime_in_progress_parallel_running(dashboard_medium):
    """Two nodes running in parallel: total counts both, wall counts the longest."""
    dashboard = dashboard_medium._dashboard
    now = time.time()
    # 1 done node (10s baseline), 2 running nodes started 4s and 2s ago
    job = _make_progress_job([
        (NodeStatus.SUCCESS, 10.0, None, 10.0),
        (NodeStatus.RUNNING, None, now - 4.0, None),
        (NodeStatus.RUNNING, None, now - 2.0, None),
    ], complete=False)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    with patch("siliconcompiler.report.dashboard.cli.board.time.time", return_value=now):
        rendered = dashboard._render_progress_bar(dashboard._layout)

    runtimes = _runtime_strings(rendered.renderables[0])

    # wall = 10 + (now - min(now-4, now-2)) = 14, total = 10 + 4 + 2 = 16
    assert runtimes == [("0:14.0", "0:16.0")]


def test_progress_bar_runtime_resumed_job_uses_recorded_totaltime(dashboard_medium):
    """A resumed job: prior-session done nodes contribute via totaltime metric.

    The two prior-session nodes are strictly sequential (intervals [0, 40] and
    [40, 90]) so no parallelism is detected — this isolates the resumed wall-time
    computation across a session boundary from the parallelism display path.
    """
    dashboard = dashboard_medium._dashboard
    now = time.time()
    # Prior session: two sequential nodes. Final wall checkpoint = 90.
    # Resume and a new node starts now - 5s ago.
    job = _make_progress_job([
        (NodeStatus.SUCCESS, 40.0, None, 40.0),    # prior session, interval [0, 40]
        (NodeStatus.SUCCESS, 50.0, None, 90.0),    # prior session, interval [40, 90]
        (NodeStatus.RUNNING, None, now - 5.0, None),  # this session
    ], complete=False)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    with patch("siliconcompiler.report.dashboard.cli.board.time.time", return_value=now):
        rendered = dashboard._render_progress_bar(dashboard._layout)

    runtimes = _runtime_strings(rendered.renderables[0])

    # wall = 90 (baseline) + 5 (active) = 95, total = 40 + 50 + 5 = 95
    # No parallelism (sequential intervals + single running) -> wall column only.
    assert runtimes == [("1:35.0", "")]


def test_progress_bar_runtime_sequential_done_one_running_no_wall(dashboard_medium):
    """No two tasks ever overlapped (sequential done + single running) => single value."""
    dashboard = dashboard_medium._dashboard
    now = time.time()
    job = _make_progress_job([
        (NodeStatus.SUCCESS, 5.0, None, 5.0),    # interval [0, 5]
        (NodeStatus.SUCCESS, 5.0, None, 10.0),   # interval [5, 10]
        (NodeStatus.RUNNING, None, now - 2.0, None),  # only one running, no overlap
    ], complete=False)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    with patch("siliconcompiler.report.dashboard.cli.board.time.time", return_value=now):
        rendered = dashboard._render_progress_bar(dashboard._layout)

    runtimes = _runtime_strings(rendered.renderables[0])
    assert runtimes[0][1] == ""  # cpu column empty -> no parallelism


def test_progress_bar_runtime_two_running_triggers_wall(dashboard_medium):
    """Two simultaneously-running nodes (no done history) trigger wall display."""
    dashboard = dashboard_medium._dashboard
    now = time.time()
    job = _make_progress_job([
        (NodeStatus.RUNNING, None, now - 3.0, None),
        (NodeStatus.RUNNING, None, now - 2.0, None),
    ], complete=False)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    with patch("siliconcompiler.report.dashboard.cli.board.time.time", return_value=now):
        rendered = dashboard._render_progress_bar(dashboard._layout)

    runtimes = _runtime_strings(rendered.renderables[0])
    assert runtimes[0][1] != ""  # cpu column populated -> parallelism detected


def test_progress_bar_runtime_overlapping_done_triggers_wall(dashboard_medium):
    """Two completed nodes with overlapping wall intervals trigger wall display."""
    dashboard = dashboard_medium._dashboard
    # node A: wall interval [0, 10] (totaltime=10, tasktime=10)
    # node B: wall interval [5, 15] (totaltime=15, tasktime=10) -> overlaps [5, 10]
    job = _make_progress_job([
        (NodeStatus.SUCCESS, 10.0, None, 10.0),
        (NodeStatus.SUCCESS, 10.0, None, 15.0),
    ], complete=True)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project, complete=True)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    rendered = dashboard._render_progress_bar(dashboard._layout)
    runtimes = _runtime_strings(rendered.renderables[0])
    assert runtimes[0][1] != ""


def test_progress_bar_runtime_no_data_shows_zero(dashboard_medium):
    """Pending job with no data: both total and wall are 0, single value displayed."""
    dashboard = dashboard_medium._dashboard
    job = _make_progress_job([
        (NodeStatus.PENDING, None, None, None),
        (NodeStatus.PENDING, None, None, None),
    ], complete=False)

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = job
        dashboard._update_render_data(dashboard_medium._project)

    dashboard._update_rendable_data()
    dashboard._update_layout()

    rendered = dashboard._render_progress_bar(dashboard._layout)
    runtimes = _runtime_strings(rendered.renderables[0])

    assert runtimes == [("0:00.0", "")]


def test_get_job_records_totaltime_metric(mock_project, fake_console):
    """_get_job should populate node['time']['totaltime'] from the totaltime metric."""
    mock_project.set("record", "status", "success", step="route.global", index=0)
    mock_project.set("metric", "tasktime", 12.5, step="route.global", index=0)
    mock_project.set("metric", "totaltime", 42.0, step="route.global", index=0)

    dashboard = MPManager.get_dashboard()
    job = dashboard._get_job(mock_project)

    matched = [n for n in job.nodes if n["step"] == "route.global"]
    assert len(matched) == 1
    assert matched[0]["time"]["duration"] == 12.5
    assert matched[0]["time"]["totaltime"] == 42.0


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


def test_get_job_topology_cached(mock_project, fake_console):
    """Repeated _get_job calls on the same project must reuse the cached
    flowgraph topology rather than re-running the recursive distance walk.

    The cache key is the design/jobname pair; status changes that don't
    introduce/remove SKIPPED nodes must hit the cache.
    """
    dashboard = MPManager.get_dashboard()

    dashboard._get_job(mock_project)
    project_id = "test_design/test_job"
    assert project_id in dashboard._topology_cache
    cached = dashboard._topology_cache[project_id]

    # A status flip that is NOT skipped must reuse the cached topology
    # (same object identity).
    mock_project.set("record", "status", "success", step="route.global", index=0)
    dashboard._get_job(mock_project)
    assert dashboard._topology_cache[project_id] is cached

    mock_project.set("record", "status", "error", step="write.views", index=0)
    dashboard._get_job(mock_project)
    assert dashboard._topology_cache[project_id] is cached


def test_get_job_topology_invalidated_by_skipped(mock_project, fake_console):
    """Introducing a SKIPPED node changes which inputs downstream nodes see
    (RuntimeFlowgraph.get_node_inputs walks past skipped predecessors), so
    the topology cache must be rebuilt when the SKIPPED set changes."""
    dashboard = MPManager.get_dashboard()

    dashboard._get_job(mock_project)
    project_id = "test_design/test_job"
    first = dashboard._topology_cache[project_id]

    mock_project.set("record", "status", "skipped", step="route.detailed", index=0)
    dashboard._get_job(mock_project)
    second = dashboard._topology_cache[project_id]

    assert second is not first
    assert first.signature != second.signature


def test_get_job_topology_distance_walk_runs_once(mock_project, fake_console,
                                                  monkeypatch):
    """The recursive `get_node_distance` walk inside `_get_flow_topology`
    is the expensive piece we're trying to avoid. After the first call
    seeds the cache, status-only refreshes must not call it again.

    Uses `RuntimeFlowgraph.get_execution_order` as a miss-only sentinel:
    it is invoked exclusively from the cache-miss branch of
    `_get_flow_topology`, so its call count equals the number of real
    rebuilds. We also pin object identity to catch in-place rebuilds that
    a presence-only check (`project_id in _topology_cache`) would miss.
    """
    dashboard = MPManager.get_dashboard()
    real_get_exec_order = RuntimeFlowgraph.get_execution_order
    exec_calls = []

    def counting(self, *args, **kwargs):
        exec_calls.append(self)
        return real_get_exec_order(self, *args, **kwargs)

    monkeypatch.setattr(RuntimeFlowgraph, "get_execution_order", counting)

    # First call: cache miss — get_execution_order must be invoked.
    dashboard._get_job(mock_project)
    after_seed = len(exec_calls)
    assert after_seed >= 1
    seeded = dashboard._topology_cache["test_design/test_job"]

    # Status-only refreshes: cache hits — must reuse the same _FlowTopology
    # object and must not invoke get_execution_order again.
    dashboard._get_job(mock_project)
    mock_project.set("record", "status", "running",
                     step="floorplan.init", index=0)
    dashboard._get_job(mock_project)
    mock_project.set("record", "status", "success",
                     step="floorplan.init", index=0)
    dashboard._get_job(mock_project)

    assert len(exec_calls) == after_seed, (
        f"get_execution_order called {len(exec_calls)} times, expected "
        f"{after_seed} (one per real topology rebuild)"
    )
    assert dashboard._topology_cache["test_design/test_job"] is seeded, (
        "Topology object identity changed despite no structural change"
    )


def test_get_job_status_counts_correct_with_cache(mock_project, fake_console):
    """Status-derived counters (success/error/finished/visible) must update
    on every call even when the topology cache is reused — they are
    deliberately *not* part of the cache."""
    dashboard = MPManager.get_dashboard()

    job0 = dashboard._get_job(mock_project)
    assert job0.success == 0
    assert job0.finished == 0

    mock_project.set("record", "status", "success", step="route.global", index=0)
    job1 = dashboard._get_job(mock_project)
    assert job1.success == 1
    assert job1.finished == 1

    mock_project.set("record", "status", "error", step="write.views", index=0)
    job2 = dashboard._get_job(mock_project)
    assert job2.error == 1
    assert job2.success == 1
    assert job2.finished == 2


def test_get_job_priority_reflects_status_changes(mock_project, fake_console):
    """node_priority is recomputed from cached node_dists on every call so
    that running/error nodes float to the top of the display even though
    the underlying topology was cached."""
    dashboard = MPManager.get_dashboard()

    # First call: nothing is running, nothing has errored, so entry nodes
    # are the only priority-0 nodes.
    job_initial = dashboard._get_job(mock_project)
    initial_priorities = {
        (node["step"], node["index"]): node["print"]["priority"]
        for node in job_initial.nodes
    }

    # Pick a deep, non-entry node to set ERROR on; its priority should
    # drop to 0 (errors are part of the priority-0 startnode set).
    target = ("write.views", "0")
    assert initial_priorities.get(target, 1) > 0

    mock_project.set("record", "status", "error",
                     step=target[0], index=target[1])
    job_after = dashboard._get_job(mock_project)

    after_priorities = {
        (node["step"], node["index"]): node["print"]["priority"]
        for node in job_after.nodes
    }
    assert after_priorities[target] == 0


def test_get_job_separate_projects_use_separate_cache_entries(
        mock_project, fake_console):
    """The cache key is design/jobname; two distinct projects must each
    get their own cached topology."""
    dashboard = MPManager.get_dashboard()

    dashboard._get_job(mock_project)
    assert "test_design/test_job" in dashboard._topology_cache

    mock_project.set('option', 'jobname', 'other_job')
    dashboard._get_job(mock_project)
    assert "test_design/other_job" in dashboard._topology_cache
    assert "test_design/test_job" in dashboard._topology_cache


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


# ---------------------------------------------------------------------------
# LogBufferHandler.formatter_source
# ---------------------------------------------------------------------------

def _info_record(msg="hello"):
    return logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=None, exc_info=None)


def test_log_buffer_handler_uses_own_formatter_when_no_source():
    buffer = LogBuffer(queue.Queue(), n=10)
    handler = buffer.make_handler(None)
    handler.setFormatter(logging.Formatter("OWN:%(message)s"))

    assert handler.format(_info_record("hi")) == "OWN:hi"


def test_log_buffer_handler_delegates_to_formatter_source():
    """When formatter_source is set, the handler formats with the source's
    current formatter rather than its own."""
    source = logging.Handler()
    source.setFormatter(logging.Formatter("SRC:%(message)s"))

    buffer = LogBuffer(queue.Queue(), n=10)
    handler = buffer.make_handler(None, formatter_source=source)
    handler.setFormatter(logging.Formatter("OWN:%(message)s"))

    assert handler.format(_info_record("hi")) == "SRC:hi"


def test_log_buffer_handler_tracks_source_formatter_changes():
    """The whole point of formatter_source: when the source's formatter is
    swapped out mid-run, the dashboard handler picks up the new formatter
    on its very next emit, with no explicit synchronization."""
    source = logging.Handler()
    source.setFormatter(logging.Formatter("A:%(message)s"))

    buffer = LogBuffer(queue.Queue(), n=10)
    handler = buffer.make_handler(None, formatter_source=source)

    assert handler.format(_info_record("hi")) == "A:hi"
    source.setFormatter(logging.Formatter("B:%(message)s"))
    assert handler.format(_info_record("hi")) == "B:hi"


def test_log_buffer_handler_falls_back_when_source_has_no_formatter():
    """If formatter_source is set but the source has no formatter attached,
    fall back to the handler's own formatter rather than raising."""
    source = logging.Handler()  # no formatter set

    buffer = LogBuffer(queue.Queue(), n=10)
    handler = buffer.make_handler(None, formatter_source=source)
    handler.setFormatter(logging.Formatter("OWN:%(message)s"))

    assert handler.format(_info_record("hi")) == "OWN:hi"


# ---------------------------------------------------------------------------
# CliDashboard set_logger / _detach_logger
# ---------------------------------------------------------------------------

def test_set_logger_adds_dashboard_handler_without_removing_terminal(
        mock_project, fake_console):
    """Attaching must not swap or detach the project's terminal handler —
    other components (scheduler, slurm, docker, remote) hold references to
    it and would break if it disappeared."""
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)
    terminal = mock_project._logger_console

    dash.set_logger(mock_project.logger)

    assert mock_project._logger_console is terminal, \
        "terminal handler must not be swapped"
    assert terminal in mock_project.logger.handlers
    assert dash._dashboard_handler in mock_project.logger.handlers
    assert dash._terminal_handler is terminal


def test_set_logger_installs_active_suppress_filter(mock_project, fake_console):
    """The terminal handler stays attached but is silenced via a filter so
    its writes don't corrupt the rich Live display."""
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)

    dash.set_logger(mock_project.logger)

    assert dash._suppress_filter in mock_project._logger_console.filters
    assert dash._suppress_filter.active is True


def test_set_logger_idempotent_on_repeat_call(mock_project, fake_console):
    """Calling set_logger twice with the same logger must not double-attach
    the handler or stack duplicate filters."""
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)

    dash.set_logger(mock_project.logger)
    first_handler = dash._dashboard_handler

    dash.set_logger(mock_project.logger)

    assert dash._dashboard_handler is first_handler
    assert mock_project.logger.handlers.count(first_handler) == 1
    assert mock_project._logger_console.filters.count(dash._suppress_filter) == 1


def test_set_logger_moves_handler_when_swapping_loggers(mock_project, fake_console):
    """Re-attaching to a different logger must move the dashboard handler
    rather than leaving it leaked on the old one. The project's logger is
    invariant in practice, but the move keeps the contract self-consistent."""
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)

    dash.set_logger(mock_project.logger)
    handler = dash._dashboard_handler
    other = logging.getLogger("test_set_logger_moves_handler_when_swapping_loggers")
    other.handlers = []

    dash.set_logger(other)

    assert dash._dashboard_handler is handler
    assert handler not in mock_project.logger.handlers
    assert handler in other.handlers
    assert dash._logger is other


def test_set_logger_none_detaches(mock_project, fake_console):
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)

    dash.set_logger(mock_project.logger)
    attached = dash._dashboard_handler
    assert attached is not None

    dash.set_logger(None)

    assert dash._dashboard_handler is None
    assert attached not in mock_project.logger.handlers
    assert dash._suppress_filter not in mock_project._logger_console.filters
    assert dash._suppress_filter.active is False


def test_detach_logger_undoes_attach(mock_project, fake_console):
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)
    terminal = mock_project._logger_console
    handlers_before = list(mock_project.logger.handlers)

    dash.set_logger(mock_project.logger)
    dash._detach_logger()

    assert list(mock_project.logger.handlers) == handlers_before
    assert terminal.filters == []
    assert dash._dashboard_handler is None
    assert dash._terminal_handler is None
    assert dash._suppress_filter.active is False


def test_detach_logger_is_idempotent(mock_project, fake_console):
    """Calling _detach_logger when nothing is attached must not raise."""
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)

    dash._detach_logger()
    dash._detach_logger()


def test_attach_detach_attach_cycle(mock_project, fake_console):
    """A second attach after detach should produce the same end-state as
    the first — this is what the future user-quit + resume path relies on."""
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)
    terminal = mock_project._logger_console

    dash.set_logger(mock_project.logger)
    first_handler = dash._dashboard_handler
    dash._detach_logger()
    dash.set_logger(mock_project.logger)
    second_handler = dash._dashboard_handler

    assert second_handler is not None
    # The handler instance may be reused or new — either is fine. What
    # matters is the end-state: attached to logger, filter active.
    assert second_handler in mock_project.logger.handlers
    assert dash._suppress_filter in terminal.filters
    assert dash._suppress_filter.active is True
    # And the first handler should not be lingering on the logger.
    if second_handler is not first_handler:
        assert first_handler not in mock_project.logger.handlers


def test_terminal_output_suppressed_during_attach_resumed_after_detach(
        mock_project, fake_console):
    """End-to-end: records reach the terminal stream before attach, are
    silenced while attached, and flow again after detach."""
    with patch("threading.Thread"):
        dash = CliDashboard(mock_project)
    terminal = mock_project._logger_console

    # Redirect the terminal handler's stream so we can inspect what it wrote.
    captured = io.StringIO()
    terminal.stream = captured

    mock_project.logger.info("BEFORE")
    before_len = len(captured.getvalue())
    assert "BEFORE" in captured.getvalue()

    dash.set_logger(mock_project.logger)
    mock_project.logger.info("DURING")
    # Nothing new should have been written to the terminal stream.
    assert len(captured.getvalue()) == before_len

    dash._detach_logger()
    mock_project.logger.info("AFTER")
    assert "AFTER" in captured.getvalue()


def test_should_disable_no_flow():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_file("top.v")

    proj = Project(design)

    # No flow set, so there is nothing to inspect.
    assert CliDashboard.should_disable(proj) is False


def test_should_disable_no_breakpoint():
    proj = _project_with_flow()

    assert CliDashboard.should_disable(proj) is False


def test_should_disable_with_breakpoint(project_logger, caplog):
    proj = _project_with_flow()

    project_logger(proj)

    proj.set("option", "breakpoint", True, step="faux")

    assert CliDashboard.should_disable(proj) is True
    assert "Disabling dashboard due to breakpoints at: faux/0" in caplog.text
