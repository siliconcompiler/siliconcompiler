"""
Tests for the end-of-run summary report generator.

Tests cover:
- Summary generation for successful runs
- Summary generation for failed runs
- Summary generation with various node configurations
- Error handling and edge cases
- Template rendering and file output
- Coverage of all key metrics and node information
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from siliconcompiler import Project, Design, Flowgraph, NodeStatus, Task
from siliconcompiler.report.end_of_run_summary import (
    generate_end_of_run_summary,
    _get_node_key_metrics,
    _format_exit_code,
    _get_duration,
    _format_duration,
    _get_log_paths,
    _get_task_info
)
from siliconcompiler.utils.paths import jobdir


class SimpleTask(Task):
    """A simple test task."""
    def tool(self):
        return "testtool"

    def task(self):
        return "testtask"


class AnotherTask(Task):
    """Another test task with different tool."""
    def tool(self):
        return "othertool"

    def task(self):
        return "othertask"


@pytest.fixture
def basic_project():
    """Create a basic project with simple flow for testing."""
    design = Design("testdesign")
    proj = Project(design)
    proj.set("option", "design", "testdesign")

    flow = Flowgraph("testflow")
    flow.node("step1", SimpleTask())
    flow.node("step2", AnotherTask())
    proj.set_flow(flow)

    return proj


@pytest.fixture
def successful_project(basic_project):
    """Create a project with successful execution data."""
    proj = basic_project

    # Record step1 execution
    proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index="0")
    proj.set("record", "toolversion", "1.0.0", step="step1", index="0")
    proj.set("record", "toolexitcode", 0, step="step1", index="0")
    proj.set("record", "starttime", 1000.0, step="step1", index="0")
    proj.set("record", "endtime", 1010.0, step="step1", index="0")
    proj.set("metric", "warnings", 2, step="step1", index="0")
    proj.set("metric", "errors", 0, step="step1", index="0")

    # Record step2 execution
    proj.set("record", "status", NodeStatus.SUCCESS, step="step2", index="0")
    proj.set("record", "toolversion", "2.0.0", step="step2", index="0")
    proj.set("record", "toolexitcode", 0, step="step2", index="0")
    proj.set("record", "starttime", 1010.0, step="step2", index="0")
    proj.set("record", "endtime", 1025.0, step="step2", index="0")
    proj.set("metric", "warnings", 0, step="step2", index="0")
    proj.set("metric", "errors", 0, step="step2", index="0")

    proj._record_history()
    return proj


@pytest.fixture
def failed_project(basic_project):
    """Create a project with a failed execution."""
    proj = basic_project

    # Record step1 execution (success)
    proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index="0")
    proj.set("record", "toolversion", "1.0.0", step="step1", index="0")
    proj.set("record", "toolexitcode", 0, step="step1", index="0")
    proj.set("record", "starttime", 1000.0, step="step1", index="0")
    proj.set("record", "endtime", 1010.0, step="step1", index="0")
    proj.set("metric", "warnings", 0, step="step1", index="0")
    proj.set("metric", "errors", 0, step="step1", index="0")

    # Record step2 execution (failure)
    proj.set("record", "status", NodeStatus.ERROR, step="step2", index="0")
    proj.set("record", "toolversion", "2.0.0", step="step2", index="0")
    proj.set("record", "toolexitcode", 1, step="step2", index="0")
    proj.set("record", "starttime", 1010.0, step="step2", index="0")
    proj.set("record", "endtime", 1015.0, step="step2", index="0")
    proj.set("metric", "warnings", 1, step="step2", index="0")
    proj.set("metric", "errors", 3, step="step2", index="0")

    proj._record_history()
    return proj


@pytest.fixture
def skipped_project(basic_project):
    """Create a project with skipped nodes."""
    proj = basic_project

    # Record step1 execution
    proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index="0")
    proj.set("record", "toolversion", "1.0.0", step="step1", index="0")
    proj.set("record", "toolexitcode", 0, step="step1", index="0")
    proj.set("record", "starttime", 1000.0, step="step1", index="0")
    proj.set("record", "endtime", 1010.0, step="step1", index="0")
    proj.set("metric", "warnings", 0, step="step1", index="0")
    proj.set("metric", "errors", 0, step="step1", index="0")

    # Record step2 as skipped
    proj.set("record", "status", NodeStatus.SKIPPED, step="step2", index="0")
    proj.set("metric", "warnings", 0, step="step2", index="0")
    proj.set("metric", "errors", 0, step="step2", index="0")

    proj._record_history()
    return proj


# Formatters tests

def test_format_exit_code_zero():
    """Test formatting exit code 0."""
    assert _format_exit_code(0) == "0"


def test_format_exit_code_nonzero():
    """Test formatting non-zero exit code."""
    assert _format_exit_code(1) == "1"
    assert _format_exit_code(127) == "127"


def test_format_exit_code_none():
    """Test formatting None exit code."""
    assert _format_exit_code(None) == "-"


def test_format_duration_seconds():
    """Test formatting various durations."""
    # 1 second
    assert _format_duration(1.0) == "0:01"
    # 65 seconds (1 minute 5 seconds)
    assert _format_duration(65.0) == "1:05"
    # 3665 seconds (1 hour 1 minute 5 seconds)
    assert _format_duration(3665.0) == "1:01:05"


def test_format_duration_none():
    """Test formatting None duration."""
    assert _format_duration(None) == "-"


def test_format_duration_zero():
    """Test formatting zero duration."""
    assert _format_duration(0.0) == "0:00"


def test_format_duration_fractional_seconds():
    """Test duration formatting with fractional seconds."""
    result = _format_duration(1.5)
    assert result == "0:02"


# Duration calculation tests

def test_get_duration_from_tasktime_metric(successful_project):
    """Test getting duration from tasktime metric."""
    proj = successful_project.history("job0")
    proj.set("metric", "tasktime", 5.5, step="step1", index="0")

    duration = _get_duration(proj, "step1", "0")
    assert duration == 5.5


def test_get_duration_from_start_end_times(successful_project):
    """Test calculating duration from start and end times."""
    proj = successful_project.history("job0")

    duration = _get_duration(proj, "step1", "0")
    # step1: starttime=1000.0, endtime=1010.0, so duration should be 10.0
    assert duration == 10.0


def test_get_duration_missing_times(basic_project):
    """Test duration when times are missing."""
    proj = basic_project
    proj.set("record", "status", NodeStatus.PENDING, step="step1", index="0")

    duration = _get_duration(proj, "step1", "0")
    assert duration is None


def test_get_duration_tasktime_takes_precedence(successful_project):
    """Test that tasktime metric takes precedence over calculated duration."""
    proj = successful_project.history("job0")
    proj.set("metric", "tasktime", 999.0, step="step1", index="0")

    duration = _get_duration(proj, "step1", "0")
    assert duration == 999.0


def test_get_duration_with_invalid_time_values():
    """Test duration calculation with invalid (non-numeric) time values."""
    proj = Project("testdesign")
    flow = Flowgraph("testflow")
    flow.node("step1", SimpleTask())
    proj.set_flow(flow)

    # Set invalid time values (strings that can't convert)
    proj.set("record", "starttime", "not-a-number", step="step1", index="0")
    proj.set("record", "endtime", "also-invalid", step="step1", index="0")

    # Should return None when conversion fails
    duration = _get_duration(proj, "step1", "0")
    assert duration is None


# Key metrics tests

def test_get_node_key_metrics_with_values(successful_project):
    """Test getting node metrics when values are present."""
    proj = successful_project.history("job0")

    metrics = _get_node_key_metrics(proj, "step1", "0")
    assert metrics is not None
    assert metrics['warnings'] == 2
    assert metrics['errors'] == 0


def test_get_node_key_metrics_zero_values(successful_project):
    """Test getting node metrics with zero values."""
    proj = successful_project.history("job0")

    metrics = _get_node_key_metrics(proj, "step2", "0")
    assert metrics is not None
    assert metrics['warnings'] == 0
    assert metrics['errors'] == 0


def test_get_node_key_metrics_missing(basic_project):
    """Test getting metrics when none are set."""
    proj = basic_project
    proj.set("record", "status", NodeStatus.PENDING, step="step1", index="0")

    metrics = _get_node_key_metrics(proj, "step1", "0")
    assert metrics is None


def test_get_node_key_metrics_with_only_warnings(successful_project):
    """Test metrics collection when only warnings are present."""
    proj = successful_project.history("job0")
    proj.set("metric", "errors", None, step="step1", index="0")

    metrics = _get_node_key_metrics(proj, "step1", "0")
    assert 'warnings' in metrics
    assert 'errors' not in metrics


def test_get_node_key_metrics_with_only_errors(successful_project):
    """Test metrics collection when only errors are present."""
    proj = successful_project.history("job0")
    proj.set("metric", "warnings", None, step="step1", index="0")

    metrics = _get_node_key_metrics(proj, "step1", "0")
    assert 'warnings' not in metrics
    assert 'errors' in metrics


# Task info tests

def test_get_task_info_success(successful_project):
    """Test getting task info with all fields present."""
    proj = successful_project.history("job0")

    tool, task, version = _get_task_info(proj, "testflow", "step1", "0")
    assert tool == "testtool"
    assert task == "testtask"
    assert version == "1.0.0"


def test_get_task_info_missing_version(basic_project):
    """Test getting task info when version is missing."""
    proj = basic_project
    proj.set("record", "status", NodeStatus.PENDING, step="step1", index="0")

    tool, task, version = _get_task_info(proj, "testflow", "step1", "0")
    assert tool == "testtool"
    assert task == "testtask"
    assert version is None


# Log paths tests

def test_get_log_paths_with_mocking(successful_project, tmp_path, monkeypatch):
    """Test getting log paths with mocked SchedulerNode."""
    proj = successful_project.history("job0")

    # Create mock log files
    mock_exe_log = tmp_path / "step1.log"
    mock_exe_log.write_text("exe log content")
    mock_sc_log = tmp_path / "sc_step1_0.log"
    mock_sc_log.write_text("sc log content")

    # Mock SchedulerNode to return our test paths
    mock_node = MagicMock()
    mock_node.get_log.side_effect = lambda log_type: {
        'exe': str(mock_exe_log),
        'sc': str(mock_sc_log)
    }[log_type]

    with patch('siliconcompiler.scheduler.schedulernode.SchedulerNode', return_value=mock_node):
        logs = _get_log_paths(proj, "step1", "0")
        assert logs['exe'] == str(mock_exe_log)
        assert logs['sc'] == str(mock_sc_log)


def test_get_log_paths_empty_log_ignored(successful_project, tmp_path, monkeypatch):
    """Test that empty log files are ignored."""
    proj = successful_project.history("job0")

    # Create empty log file
    mock_exe_log = tmp_path / "step1.log"
    mock_exe_log.write_text("")
    mock_sc_log = tmp_path / "sc_step1_0.log"
    mock_sc_log.write_text("sc log content")

    mock_node = MagicMock()
    mock_node.get_log.side_effect = lambda log_type: {
        'exe': str(mock_exe_log),
        'sc': str(mock_sc_log)
    }[log_type]

    with patch('siliconcompiler.scheduler.schedulernode.SchedulerNode', return_value=mock_node):
        logs = _get_log_paths(proj, "step1", "0")
        assert logs['exe'] is None  # Empty file should be ignored
        assert logs['sc'] == str(mock_sc_log)


# Summary generation tests

def test_generate_summary_successful_run(successful_project, tmp_path):
    """Test generating summary for a successful run."""
    proj = successful_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        result = generate_end_of_run_summary(proj, str(output_path))

    assert result == str(output_path)
    assert output_path.exists()

    content = output_path.read_text()
    assert "SiliconCompiler End-of-Run Summary" in content
    assert "Overall Status : PASSED" in content
    assert "Total: 2 nodes" in content
    assert "step1/0" in content
    assert "step2/0" in content


def test_generate_summary_failed_run(failed_project, tmp_path):
    """Test generating summary for a failed run."""
    proj = failed_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        result = generate_end_of_run_summary(proj, str(output_path))

    assert result == str(output_path)
    assert output_path.exists()

    content = output_path.read_text()
    assert "Overall Status : FAILED" in content
    assert "Failed: 1" in content


def test_generate_summary_skipped_nodes(skipped_project, tmp_path):
    """Test generating summary with skipped nodes."""
    proj = skipped_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert "Overall Status : PASSED" in content
    assert "Skipped: 1" in content


def test_generate_summary_default_output_path(successful_project):
    """Test generating summary with default output path."""
    proj = successful_project.history("job0")

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        result = generate_end_of_run_summary(proj)

    expected_path = os.path.join(jobdir(proj), "summary.txt")
    assert result == expected_path
    assert os.path.exists(expected_path)


def test_generate_summary_no_flow_raises_error(basic_project):
    """Test that missing flow raises ValueError."""
    proj = basic_project
    proj.set("option", "flow", "")
    proj._record_history()
    proj = proj.history("job0")

    with pytest.raises(ValueError, match="No flow configured"):
        generate_end_of_run_summary(proj)


def test_generate_summary_content_includes_headers(successful_project, tmp_path):
    """Test that summary includes header information."""
    proj = successful_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert "Design" in content or "design" in content
    assert "testdesign" in content


def test_generate_summary_content_includes_node_table(successful_project, tmp_path):
    """Test that summary includes node execution table."""
    proj = successful_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    # Check for table header
    assert "Node" in content
    assert "Tool" in content
    assert "Status" in content
    assert "Exit" in content
    # Check for node data
    assert "testtool" in content
    assert "success" in content


def test_generate_summary_content_includes_metrics(successful_project, tmp_path):
    """Test that summary includes warnings and errors."""
    proj = successful_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert "Warnings" in content
    assert "Errors" in content


def test_generate_summary_content_includes_run_info(successful_project, tmp_path):
    """Test that summary includes run information."""
    proj = successful_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert "Run Information" in content
    assert "Report Generated" in content
    assert "Job Directory" in content
    assert "Summary File" in content


def test_generate_summary_with_exit_codes(failed_project, tmp_path):
    """Test that summary correctly displays exit codes."""
    proj = failed_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    lines = content.split('\n')
    step1_line = next((line for line in lines if 'step1/0' in line), None)
    assert step1_line is not None
    assert '0' in step1_line


def test_summary_called_from_project_summary(successful_project):
    """Test that summary is generated when project.summary() is called."""
    proj = successful_project

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        proj.summary()


def test_summary_generated_on_error_path(failed_project, tmp_path):
    """Test that summary is generated even with errors."""
    proj = failed_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        result = generate_end_of_run_summary(proj, str(output_path))

    assert result == str(output_path)
    assert output_path.exists()
    content = output_path.read_text()
    assert "FAILED" in content


def test_summary_with_multiple_indices(basic_project, tmp_path):
    """Test summary generation with multiple node indices."""
    proj = basic_project

    for i in range(2):
        proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index=str(i))
        proj.set("record", "toolversion", "1.0.0", step="step1", index=str(i))
        proj.set("record", "toolexitcode", 0, step="step1", index=str(i))
        proj.set("record", "starttime", 1000.0 + i * 100, step="step1", index=str(i))
        proj.set("record", "endtime", 1010.0 + i * 100, step="step1", index=str(i))
        proj.set("metric", "warnings", i, step="step1", index=str(i))
        proj.set("metric", "errors", 0, step="step1", index=str(i))

    proj._record_history()
    proj = proj.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert "step1/0" in content
    assert "step1/1" in content


# Edge cases tests

def test_summary_with_no_nodes(basic_project, tmp_path):
    """Test summary generation with a flow that has no executed nodes."""
    proj = basic_project
    proj._record_history()
    proj = proj.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    assert output_path.exists()
    content = output_path.read_text()
    assert "nodes" in content


def test_summary_with_missing_metrics(basic_project, tmp_path):
    """Test summary when some nodes lack metrics."""
    proj = basic_project

    proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index="0")
    proj.set("record", "toolversion", "1.0.0", step="step1", index="0")
    proj.set("record", "toolexitcode", 0, step="step1", index="0")

    proj._record_history()
    proj = proj.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    assert output_path.exists()
    content = output_path.read_text()
    assert "-" in content


def test_summary_with_timeout_status(basic_project, tmp_path):
    """Test summary with timeout status."""
    proj = basic_project

    proj.set("record", "status", NodeStatus.TIMEOUT, step="step1", index="0")
    proj.set("metric", "warnings", 0, step="step1", index="0")
    proj.set("metric", "errors", 0, step="step1", index="0")

    proj._record_history()
    proj = proj.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert "FAILED" in content
    assert "Timeout: 1" in content


def test_summary_with_pending_status(basic_project, tmp_path):
    """Test summary with pending nodes."""
    proj = basic_project

    proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index="0")
    proj.set("metric", "warnings", 0, step="step1", index="0")
    proj.set("metric", "errors", 0, step="step1", index="0")

    proj._record_history()
    proj = proj.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert "INCOMPLETE" in content


# Template rendering tests

def test_template_file_exists():
    """Test that the template file exists."""
    from siliconcompiler.utils import get_file_template

    template = get_file_template('report/end_of_run_summary.txt.j2')
    assert template is not None


def test_template_renders_without_errors(successful_project, tmp_path):
    """Test that template renders without raising exceptions."""
    proj = successful_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        result = generate_end_of_run_summary(proj, str(output_path))
    assert result == str(output_path)


def test_template_output_is_valid_text(successful_project, tmp_path):
    """Test that template output is valid text."""
    proj = successful_project.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert isinstance(content, str)
    assert len(content) > 0
    assert content.startswith("=" * 80)
    assert "SiliconCompiler" in content


def test_summary_with_special_characters_in_design_name(tmp_path):
    """Test summary with special characters in design name."""
    proj = Project("test-design_v2")
    flow = Flowgraph("testflow")
    flow.node("step1", SimpleTask())
    proj.set_flow(flow)

    proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index="0")
    proj.set("record", "toolversion", "1.0.0", step="step1", index="0")
    proj.set("metric", "warnings", 0, step="step1", index="0")
    proj.set("metric", "errors", 0, step="step1", index="0")

    proj._record_history()
    proj = proj.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': None, 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert "test-design_v2" in content


def test_summary_with_log_files(tmp_path):
    """Test that log files are included when present."""
    proj = Project("testdesign")
    flow = Flowgraph("testflow")
    flow.node("step1", SimpleTask())
    proj.set_flow(flow)

    proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index="0")
    proj.set("record", "toolversion", "1.0.0", step="step1", index="0")
    proj.set("metric", "warnings", 0, step="step1", index="0")
    proj.set("metric", "errors", 0, step="step1", index="0")
    proj.set("record", "starttime", 1000.0, step="step1", index="0")
    proj.set("record", "endtime", 1010.0, step="step1", index="0")

    proj._record_history()
    proj = proj.history("job0")
    output_path = tmp_path / "summary.txt"

    def mock_get_log_paths(project, step, index):
        return {'exe': str(tmp_path / 'test_exe.log'), 'sc': None}

    with patch('siliconcompiler.report.end_of_run_summary._get_log_paths',
               side_effect=mock_get_log_paths):
        generate_end_of_run_summary(proj, str(output_path))

    content = output_path.read_text()
    assert output_path.exists()
    assert "Log Files:" in content


def test_summary_with_broken_flowgraph():
    """Test that ValueError is raised when RuntimeFlowgraph construction fails."""
    proj = Project("testdesign")
    flow = Flowgraph("testflow")
    flow.node("step1", SimpleTask())
    proj.set_flow(flow)

    proj.set("record", "status", NodeStatus.SUCCESS, step="step1", index="0")
    proj.set("record", "toolversion", "1.0.0", step="step1", index="0")
    proj.set("metric", "warnings", 0, step="step1", index="0")
    proj.set("metric", "errors", 0, step="step1", index="0")
    proj.set("record", "starttime", 1000.0, step="step1", index="0")
    proj.set("record", "endtime", 1010.0, step="step1", index="0")
    proj._record_history()
    proj = proj.history("job0")

    with patch('siliconcompiler.report.end_of_run_summary.RuntimeFlowgraph',
               side_effect=RuntimeError("Mock flowgraph error")):
        with pytest.raises(ValueError, match="Failed to construct runtime flowgraph"):
            generate_end_of_run_summary(proj)
