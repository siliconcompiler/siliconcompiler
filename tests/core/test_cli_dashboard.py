import pytest
from unittest.mock import Mock, patch
import threading
import logging
from rich.console import Console, Group
from rich.table import Table
from rich.padding import Padding
from rich.progress import Progress

# from rich import print
import io

from siliconcompiler.report.dashboard.cli import CliDashboard, LogBufferHandler, JobData
from siliconcompiler import NodeStatus


@pytest.fixture
def mock_chip():
    chip = Mock()
    chip.design = "test_design"
    chip.logger = Mock()
    chip.logger._console = Mock()
    chip.get.side_effect = lambda *args, **kwargs: {
        ("design",): "test_design",
        ("option", "jobname"): "test_job",
        ("record", "status"): "success",
    }.get(args, None)
    return chip


@pytest.fixture
def mock_running_job():
    mock_job_data = JobData()
    mock_job_data.total = 5
    mock_job_data.success = 1
    mock_job_data.error = 1
    mock_job_data.finished = 2
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    mock_job_data.nodes = [
        {
            "step": "node1",
            "index": 0,
            "status": "success",
            "log": "node1.log",
        },
        {
            "step": "node2",
            "index": 1,
            "status": "running",
            "log": "node2.log",
        },
        {
            "step": "node3",
            "index": 2,
            "status": "error",
            "log": "node3.log",
        },
        {
            "step": "node4",
            "index": 3,
            "status": "pending",
            "log": "node4.log",
        },
        {
            "step": "node5",
            "index": 4,
            "status": "success",
            "log": "node5.log",
        },
    ]
    return mock_job_data


@pytest.fixture
def mock_finished_job_fail():
    mock_job_data = JobData()
    mock_job_data.total = 5
    mock_job_data.success = 4
    mock_job_data.error = 1
    mock_job_data.finished = 5
    mock_job_data.design = "design1"
    mock_job_data.jobname = "job1"
    mock_job_data.nodes = [
        {
            "step": "node1",
            "index": 0,
            "status": "success",
            "log": "node1.log",
        },
        {
            "step": "node2",
            "index": 1,
            "status": "success",
            "log": "node2.log",
        },
        {
            "step": "node3",
            "index": 2,
            "status": "error",
            "log": "node3.log",
        },
        {
            "step": "node4",
            "index": 3,
            "status": "success",
            "log": "node4.log",
        },
        {
            "step": "node5",
            "index": 4,
            "status": "success",
            "log": "node5.log",
        },
    ]
    return mock_job_data


@pytest.fixture
def mock_finished_job_passed():
    mock_job_data = JobData()
    mock_job_data.total = 5
    mock_job_data.success = 5
    mock_job_data.error = 1
    mock_job_data.finished = 5
    mock_job_data.nodes = []
    return mock_job_data


@pytest.fixture
def mock_console():
    with patch("rich.console.Console") as mock:
        yield mock


@pytest.fixture
def dashboard(mock_chip, mock_console):
    with patch("threading.Thread"):
        dashboard = CliDashboard(mock_chip)
        return dashboard


def test_init(dashboard):
    assert dashboard._render_data.total == 0
    assert dashboard._render_data.success == 0
    assert dashboard._render_data.error == 0


def test_set_get_logger(dashboard):
    logger = logging.getLogger("test")
    dashboard.set_logger(logger)
    assert dashboard._logger is logger


@pytest.mark.parametrize("status", [
    NodeStatus.PENDING,
    NodeStatus.QUEUED,
    NodeStatus.RUNNING,
    NodeStatus.SUCCESS,
    NodeStatus.ERROR,
    NodeStatus.SKIPPED,
    NodeStatus.TIMEOUT])
def test_format_status(status):
    assert f"[node.{status}]{status.upper()}[/]" == CliDashboard.format_status(status)


def test_format_status_unknown():
    assert "[node.notarealstatus]NOTAREALSTATUS[/]" in CliDashboard.format_status("notarealstatus")


def test_format_node():
    formatted = CliDashboard.format_node("design1", "job1", "step1", 1)
    assert "design1" in formatted
    assert "job1" in formatted
    assert "step1" in formatted
    assert "1" in formatted


def test_stop_dashboard(dashboard):
    dashboard.stop()
    assert dashboard._render_stop_event.is_set()


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


def test_update_render_data(dashboard, mock_running_job):
    with patch.object(CliDashboard, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job

        # Trigger the update
        dashboard._update_render_data()

        # Verify the total results
        with dashboard._render_data_lock:
            assert len(dashboard._render_data.jobs) == 1
            job_data = dashboard._render_data
            assert job_data.total == 5
            assert job_data.success == 1
            assert job_data.error == 1


def test_render_log_basic(mock_running_job, dashboard):
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)

    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)

    dashboard.set_logger(logger)

    # Basic Test
    logger.log(logging.INFO, "first row")
    logger.log(logging.INFO, "second row")

    log = dashboard._render_log()
    assert isinstance(log, Table)
    assert log.row_count == 2

    console.print(log)
    assert console.file.getvalue() == " first row  \n second row \n"


def test_render_log_truncte(mock_running_job, dashboard):
    """Test that it truncates all but the last 10 lines"""
    io_file = io.StringIO()
    console = Console(file=io_file, width=120)
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)

    dashboard.set_logger(logger)

    for i in range(0, 200):
        logger.log(logging.INFO, f"log row {i}")

    log = dashboard._render_log()

    assert isinstance(log, Table)
    assert log.row_count == 50

    # Check content
    console.print(log)
    actual_output = console.file.getvalue()
    actual_lines = actual_output.splitlines(keepends=True)
    for i in range(150, 200):
        assert f"log row {i}" in actual_lines[i - 150]


def test_render_job_dashboard(mock_running_job, dashboard):
    """Test that the job dashboard is created properly"""
    for n in range(1, 6):
        if n % 2 == 0:
            with open(f"node{n}.log", "w") as f:
                f.write("test")

    with patch.object(CliDashboard, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job
        dashboard._update_render_data()

        job_board = dashboard._render_job_dashboard()

        assert isinstance(job_board, Group)

        job_table = job_board.renderables[0]
        assert isinstance(job_table, Table)

        # Display only the running and errors
        assert job_table.row_count == 5

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

        expected_lines = []
        for n, node in enumerate(mock_running_job.nodes, start=1):
            if node["status"] in ["skipped"]:
                continue
            if n % 2 == 0:
                log = node["log"]
            else:
                log = ""
            status = node["status"].upper()
            job_id = "/".join(
                [
                    mock_running_job.design,
                    mock_running_job.jobname,
                    node["step"],
                    str(node["index"]),
                ]
            )
            expected_line = f"{status}{job_id}{log}".translate(
                str.maketrans("", "", " \t\n\r\f\v")
            )
            expected_lines.append(expected_line)

        assert len(actual_lines) == len(expected_lines)
        for i, (actual, expected) in enumerate(zip(actual_lines, expected_lines)):
            assert actual == expected


def test_get_rendable_running(mock_running_job, dashboard):
    with patch.object(CliDashboard, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_running_job
        dashboard.set_logger(None)
        dashboard._update_render_data()

        rendable = dashboard._get_rendable()

        assert isinstance(rendable, Group)
        assert len(rendable.renderables) == 6

        # Verify the order
        assert isinstance(rendable.renderables[0], Padding)
        # Job board is a Group of Tables
        assert isinstance(rendable.renderables[1], Group)
        assert isinstance(rendable.renderables[1].renderables[0], Table)

        assert isinstance(rendable.renderables[2], Padding)

        assert isinstance(rendable.renderables[3], Progress)

        assert isinstance(rendable.renderables[4], Padding)

        # While running display some Padding and a Table with logs,
        assert isinstance(rendable.renderables[5], Group)
        assert len(rendable.renderables[5].renderables) == 2
        assert isinstance(rendable.renderables[5].renderables[0], Padding)
        assert isinstance(rendable.renderables[5].renderables[1], Padding)


def test_get_rendable_finished_success(mock_finished_job_passed, dashboard):
    with patch.object(CliDashboard, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_passed
        dashboard._update_render_data()

        rendable = dashboard._get_rendable()

        assert isinstance(rendable, Group)
        assert len(rendable.renderables) == 6

        # Verify the order
        assert isinstance(rendable.renderables[0], Padding)

        # Nothing to display since everything passed. Print message instead
        assert isinstance(rendable.renderables[1], Padding)

        assert isinstance(rendable.renderables[2], Padding)

        assert isinstance(rendable.renderables[3], Progress)

        assert isinstance(rendable.renderables[4], Padding)

        # Print a final status message
        assert isinstance(rendable.renderables[5], Padding)


def test_get_rendable_finished_fail(mock_finished_job_fail, dashboard):
    with patch.object(CliDashboard, "_get_job") as mock_job_data:
        mock_job_data.return_value = mock_finished_job_fail
        dashboard._update_render_data()

        rendable = dashboard._get_rendable()

        assert isinstance(rendable, Group)
        assert len(rendable.renderables) == 6

        # Verify the order
        assert isinstance(rendable.renderables[0], Padding)

        # Job board is a Group of Tables
        assert isinstance(rendable.renderables[1], Group)
        assert isinstance(rendable.renderables[1].renderables[0], Table)

        assert isinstance(rendable.renderables[2], Padding)

        assert isinstance(rendable.renderables[3], Progress)

        assert isinstance(rendable.renderables[4], Padding)

        # Print a final status message
        assert isinstance(rendable.renderables[5], Padding)
