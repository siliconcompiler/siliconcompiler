import pytest
from unittest.mock import patch
import threading
import logging
from rich.console import Console, Group
from rich.table import Table
from rich.padding import Padding
from rich.progress import Progress

# from rich import print
import io

from siliconcompiler.report.dashboard.cli import CliDashboard
from siliconcompiler.report.dashboard.cli.board import (
    Board,
    LogBufferHandler,
    JobData,
    Layout,
)
from siliconcompiler import NodeStatus
import random


@pytest.fixture
def mock_chip(gcd_chip):
    gcd_chip.set('design', 'test_design')
    gcd_chip.set('option', 'jobname', 'test_job')
    return gcd_chip


@pytest.fixture
def mock_running_job_lg():
    mock_job_data = JobData()
    mock_job_data.total = 30
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    statuses = [NodeStatus.SUCCESS, NodeStatus.ERROR, NodeStatus.PENDING]
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": statuses[index % len(statuses)],
            "log": f"node{index + 1}.log",
            "metrics": ["", ""],
            "time": {
                "duration": None,
                "start": None
            },
            "print": {
                "order": (index, index),
                "priority": 0 if statuses[index % len(statuses)] == NodeStatus.ERROR else index
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
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    statuses = [NodeStatus.SUCCESS, NodeStatus.ERROR, NodeStatus.PENDING]
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": random.choice(statuses),
            "metrics": ["", ""],
            "log": f"node{index + 1}.log",
            "print": {
                "order": (index, index),
                "priority": 0 if statuses[index % len(statuses)] == NodeStatus.ERROR else index
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
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    statuses = [NodeStatus.SUCCESS, NodeStatus.ERROR]
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": statuses[index % len(statuses)],
            "metrics": ["", ""],
            "log": f"node{index + 1}.log",
            "time": {
                "duration": 5.0,
                "start": None
            },
            "print": {
                "order": (index, index),
                "priority": 0 if statuses[index % len(statuses)] == NodeStatus.ERROR else index
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
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    mock_job_data.nodes = [
        {
            "step": f"node{index + 1}",
            "index": index,
            "status": NodeStatus.SUCCESS,
            "metrics": ["", ""],
            "log": f"node{index + 1}.log",
            "time": {
                "duration": 5.0,
                "start": None
            },
            "print": {
                "order": (index, index),
                "priority": index
            }
        }
        for index in range(mock_job_data.total)
    ]
    mock_job_data.success = len(mock_job_data.nodes)
    mock_job_data.error = 0
    mock_job_data.finished = mock_job_data.success + mock_job_data.error
    return mock_job_data


@pytest.fixture
def dashboard(mock_chip):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_chip)
        return dashboard


@pytest.fixture
def dashboard_xsmall(mock_chip):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_chip)
        dashboard._dashboard._console.height = 2
        dashboard._dashboard._console.width = 120

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard.set_logger(logger)

        return dashboard


@pytest.fixture
def dashboard_small(mock_chip):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_chip)
        dashboard._dashboard._console.height = 14
        dashboard._dashboard._console.width = 120

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard.set_logger(logger)

        return dashboard


@pytest.fixture
def dashboard_medium(mock_chip):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_chip)
        dashboard._dashboard._console.height = 40
        dashboard._dashboard._console.width = 200

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard.set_logger(logger)

        return dashboard


@pytest.fixture
def dashboard_large(mock_chip):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_chip)
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
    handler = LogBufferHandler(n=2, event=event)

    record1 = logging.LogRecord("test", logging.INFO, "path", 1, "msg1", (), None)
    record2 = logging.LogRecord("test", logging.INFO, "path", 1, "msg2", (), None)

    handler.emit(record1)
    handler.emit(record2)

    lines = handler.get_lines()
    assert len(lines) == 2
    assert "msg1" in lines[0]
    assert "msg2" in lines[1]


def test_update_render_data(dashboard, mock_running_job_lg):
    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg

        # Trigger the update
        dashboard.update_manifest()

        dashboard = dashboard._dashboard

        # Verify the total results
        with dashboard._render_data_lock:
            assert len(dashboard._render_data.jobs) == 1
            job_data = dashboard._render_data
            assert job_data.total == mock_running_job_lg.total
            assert job_data.success == mock_running_job_lg.success
            assert job_data.error == mock_running_job_lg.error


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
    assert layout.progress_bar_height == 1
    assert layout.job_board_show_log is True


def test_layout_truncate_jobs():
    """When the console is not big enough for all the jobs, display the
    progress bar and as many jobs as possible.
    """

    console_height = 10
    layout = Layout()
    layout.update(height=console_height, width=300, visible_jobs=10, visible_bars=1)

    assert layout.job_board_height == 4
    assert layout.log_height == 0
    assert layout.progress_bar_height == 1
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

    assert layout.job_board_height == visible_jobs
    assert layout.progress_bar_height == visible_bars
    assert layout.log_height == (
        console_height
        - layout.padding_job_board_header
        - layout.job_board_height
        - layout.padding_job_board
        - layout.progress_bar_height
        - layout.padding_progress_bar
        - layout.padding_log
    )
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

    assert layout.job_board_height == 20
    assert layout.progress_bar_height == visible_bars
    assert layout.log_height == 74
    assert layout.job_board_show_log is True


def test_render_log_basic(mock_running_job_lg, dashboard_medium):
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._chip)

        dashboard._update_layout()

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard_medium.set_logger(logger)

        # Basic Test
        logger.log(logging.INFO, "first row")
        logger.log(logging.INFO, "second row")

        log = dashboard._render_log(dashboard._layout)
        assert isinstance(log.renderables[0], Table)
        assert isinstance(log.renderables[1], Padding)
        assert log.renderables[0].row_count == 15

        # Capture the output
        io_file = io.StringIO()
        console = Console(file=io_file, width=120)
        console.print(log)

        consoleprint = console.file.getvalue().splitlines()
        assert len(consoleprint) == 16
        assert consoleprint[0] == " first row  "
        assert consoleprint[1] == " second row "
        for n in range(2, 16):
            assert consoleprint[n].strip() == ""  # padding


def test_render_log_truncate(mock_running_job_lg, dashboard_medium):
    """Test that it truncates all but the last 10 lines"""
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard._update_render_data(dashboard_medium._chip)

        dashboard._update_layout()

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        dashboard_medium.set_logger(logger)

        for i in range(0, 200):
            logger.log(logging.INFO, f"log row {i}")

        log = dashboard._render_log(dashboard._layout)
        assert isinstance(log.renderables[0], Table)
        assert isinstance(log.renderables[1], Padding)

        assert log.renderables[0].row_count == dashboard._layout.log_height

        # Check content
        io_file = io.StringIO()
        console = Console(file=io_file, width=120)
        console.print(log)
        actual_output = console.file.getvalue()
        actual_lines = actual_output.splitlines(keepends=True)
        start_index = 200 - dashboard._layout.log_height
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
        dashboard._update_render_data(dashboard_medium._chip)

        dashboard._update_layout()

        job_board = dashboard._render_job_dashboard(dashboard._layout)

        assert isinstance(job_board, Group)

        assert len(job_board.renderables) == 2

        job_table = job_board.renderables[0]
        assert isinstance(job_table, Table)

        assert job_table.row_count == 19

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
                log = node["log"]
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
            expected_lines_all.append(expected_line)

        actual_lines = actual_lines[2:]
        assert len(actual_lines) == 19

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
            expected_lines_all[9],
            expected_lines_all[10],
            expected_lines_all[11],
            expected_lines_all[12],
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


def test_get_rendable_xsmall_dashboard_running(mock_running_job_lg, dashboard_xsmall):
    """Test that on xtra small dashboard display only the progress bar."""
    dashboard = dashboard_xsmall._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard_xsmall.set_logger(None)
        dashboard._update_render_data(dashboard_xsmall._chip)

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
        dashboard._update_render_data(dashboard_small._chip)

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        dashboard_small.set_logger(logger)

        for i in range(100):
            logger.log(logging.INFO, f"{i}th row")

        rendable = dashboard._get_rendable()

        assert isinstance(rendable, Group)
        assert len(rendable.renderables) == 3

        job_board = rendable.renderables[0]
        assert isinstance(job_board, Group)
        assert len(job_board.renderables) == 2
        assert isinstance(job_board.renderables[0], Table)
        assert isinstance(job_board.renderables[1], Padding)
        assert job_board.renderables[0].row_count == dashboard._layout.job_board_height

        progress = rendable.renderables[1]
        assert isinstance(progress, Group)
        assert len(progress.renderables) == 2
        assert isinstance(progress.renderables[0], Progress)
        assert isinstance(progress.renderables[1], Padding)

        log = rendable.renderables[2]
        assert isinstance(log, Group)
        assert len(progress.renderables) == 2
        assert isinstance(log.renderables[0], Table)
        assert isinstance(log.renderables[1], Padding)
        assert log.renderables[0].row_count == 2


def test_get_rendable_medium_dashboard_running(mock_running_job_lg, dashboard_medium):
    """On medium and large dashboards display everything, with proper padding."""
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job_lg
        dashboard_medium.set_logger(None)
        dashboard._update_render_data(dashboard_medium._chip)

        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        dashboard_medium.set_logger(logger)

        for i in range(100):
            logger.log(logging.INFO, f"{i}th row")

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
        assert job_board.renderables[0].row_count == dashboard._layout.job_board_height

        assert isinstance(progress, Group)
        assert len(progress.renderables) == 2
        assert isinstance(progress.renderables[0], Progress)
        assert isinstance(progress.renderables[1], Padding)

        assert isinstance(log.renderables[0], Table)
        assert isinstance(log.renderables[1], Padding)
        assert log.renderables[0].row_count == dashboard._layout.log_height


def test_get_rendable_xsmall_dashboard_finished_success(mock_finished_job_passed, dashboard_xsmall):
    dashboard = dashboard_xsmall._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_passed
        dashboard._update_render_data(dashboard_xsmall._chip)

        rendable = dashboard._get_rendable()

        assert isinstance(rendable, Group)
        assert len(rendable.renderables) == 1

        # Display Summary
        assert isinstance(rendable.renderables[0], Padding)


def test_get_rendable_small_dashboard_finished_success(mock_finished_job_passed, dashboard_small):
    dashboard = dashboard_small._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_passed
        dashboard._update_render_data(dashboard_small._chip)

        rendable = dashboard._get_rendable()

        assert isinstance(rendable, Group)
        assert len(rendable.renderables) == 2

        jobs = rendable.renderables[0]
        assert isinstance(jobs, Group)
        assert len(jobs.renderables) == 2
        assert isinstance(jobs.renderables[0], Table)
        assert isinstance(jobs.renderables[1], Padding)

        # Display Summary
        assert isinstance(rendable.renderables[1], Padding)


def test_get_rendable_medium_dashboard_finished_success(mock_finished_job_passed, dashboard_medium):
    dashboard = dashboard_medium._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_passed
        dashboard._update_render_data(dashboard_medium._chip)

        rendable = dashboard._get_rendable()

        assert isinstance(rendable, Group)
        assert len(rendable.renderables) == 2

        jobs = rendable.renderables[0]
        assert isinstance(jobs, Group)
        assert len(jobs.renderables) == 2
        assert isinstance(jobs.renderables[0], Table)
        assert isinstance(jobs.renderables[1], Padding)

        # Display Summary
        assert isinstance(rendable.renderables[1], Padding)


def test_get_rendable_xsmall_dashboard_finished_fail(mock_finished_job_fail, dashboard_xsmall):
    dashboard = dashboard_xsmall._dashboard

    with patch.object(Board, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_fail
        dashboard._update_render_data(dashboard_xsmall._chip)

        rendable = dashboard._get_rendable()

        assert isinstance(rendable, Group)
        assert len(rendable.renderables) == 2

        # Display Done
        progress = rendable.renderables[0]
        assert len(progress.renderables) == 2
        assert isinstance(progress.renderables[0], Progress)
        assert isinstance(progress.renderables[1], Padding)

        # Display Summary
        assert isinstance(rendable.renderables[1], Padding)
