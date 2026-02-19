"""
End-of-run summary report generator for SiliconCompiler jobs.

Generates a comprehensive text report at the end of a job run, containing
node execution details, status information, and useful links to logs and outputs.
"""

import os
from datetime import datetime
from typing import Tuple, Optional, Dict, TYPE_CHECKING

from siliconcompiler import NodeStatus
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.utils.paths import jobdir
from siliconcompiler.utils import get_file_template
from siliconcompiler.utils.units import format_time

if TYPE_CHECKING:
    from siliconcompiler import Project, Flowgraph


def _get_node_key_metrics(project: "Project", step: str, index: str) -> Optional[Dict[str, float]]:
    """
    Hook to collect key metrics for a specific node.

    Currently returns warnings and errors metrics.

    Args:
        project: The SiliconCompiler project object.
        step (str): The step name.
        index (str): The step index.

    Returns:
        Optional[Dict[str, float]]: A dictionary of metric names to values,
                                    or None if no key metrics are available.
    """
    metrics = {}

    # Get warnings and errors
    warnings = project.get('metric', 'warnings', step=step, index=index)
    if warnings is not None:
        metrics['warnings'] = warnings

    errors = project.get('metric', 'errors', step=step, index=index)
    if errors is not None:
        metrics['errors'] = errors

    return metrics if metrics else None


def _format_exit_code(exit_code: Optional[int]) -> str:
    """
    Formats an exit code for display.

    Args:
        exit_code (Optional[int]): The exit code, or None if not available.

    Returns:
        str: A formatted exit code string.
    """
    if exit_code is None:
        return "-"
    return str(exit_code)


def _get_duration(project: "Project", step: str, index: str) -> Optional[float]:
    """
    Gets the duration for a node in seconds.

    First tries to get tasktime metric. If not available, calculates from
    starttime and endtime in the record.

    Args:
        project: The SiliconCompiler project object.
        step (str): The step name.
        index (str): The step index.

    Returns:
        Optional[float]: Duration in seconds, or None if not available.
    """
    # Try tasktime metric first
    duration = project.get('metric', 'tasktime', step=step, index=index)
    if duration is not None:
        return duration

    # Fall back to calculating from start/end times
    starttime = project.get('record', 'starttime', step=step, index=index)
    endtime = project.get('record', 'endtime', step=step, index=index)

    if starttime is not None and endtime is not None:
        return endtime - starttime

    return None


def _format_duration(duration_seconds: Optional[float]) -> str:
    """
    Formats a duration in seconds as a human-readable string.

    Uses the format_time utility from siliconcompiler.utils.units to be
    consistent with the rest of SiliconCompiler.

    Args:
        duration_seconds (Optional[float]): Duration in seconds, or None.

    Returns:
        str: Formatted duration string (HH:MM:SS or "-" if None).
    """
    if duration_seconds is None:
        return "-"

    return format_time(duration_seconds, milliseconds_digits=0)


def _get_log_paths(project: "Project", step: str, index: str) -> Dict[str, Optional[str]]:
    """
    Gets the log file paths for a node using SchedulerNode.

    Args:
        project: The SiliconCompiler project object.
        step (str): The step name.
        index (str): The step index.

    Returns:
        Dict[str, Optional[str]]: Dictionary with 'exe' and 'sc' log paths,
                                  or None if not found.
    """
    from siliconcompiler.scheduler.schedulernode import SchedulerNode

    logs = {'exe': None, 'sc': None}

    node = SchedulerNode(project, step, index)

    for log_type in ['exe', 'sc']:
        log_path = node.get_log(log_type)
        if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
            logs[log_type] = log_path

    return logs


def _get_task_info(project: "Project", flow: str, step: str, index: str) -> \
        Tuple[str, str, Optional[str]]:
    """
    Gets the tool name and version for a node.

    Args:
        project: The SiliconCompiler project object.
        flow (str): The flow name.
        step (str): The step name.
        index (str): The step index.

    Returns:
        Tuple[str, str, Optional[str]]: (tool_name, task_name, tool_version) or (None, None, None).
    """
    tool = project.get('flowgraph', flow, step, index, 'tool')
    task = project.get('flowgraph', flow, step, index, 'task')
    version = project.get('record', 'toolversion', step=step, index=index)
    return (tool, task, version)


def generate_end_of_run_summary(project: "Project", output_path: Optional[str] = None) -> str:
    """
    Generates an end-of-run summary report for a completed job.

    This function creates a comprehensive text report containing:
    - Overall job status and timing
    - Per-node execution table with status, tools, exit codes, and duration
    - Links to log files for detailed inspection
    - Run configuration information

    Args:
        project: The SiliconCompiler project object.
        output_path (Optional[str]): Path to write the summary file. If None,
                                     writes to <jobdir>/summary.txt

    Returns:
        str: The path to the generated summary file.

    Raises:
        ValueError: If no flowgraph or execution data is available.
    """
    # Get basic job information
    design = project.get("option", "design")
    jobname = project.get("option", "jobname")
    flow = project.get("option", "flow")

    if not flow:
        raise ValueError("No flow configured for summary generation")

    # Determine output path
    if output_path is None:
        job_dir = jobdir(project)
        os.makedirs(job_dir, exist_ok=True)
        output_path = os.path.join(job_dir, "summary.txt")

    # Get flowgraph and runtime information
    flowgraph: Flowgraph = project.get("flowgraph", flow, field='schema')
    try:
        runtime_flow = RuntimeFlowgraph(
            flowgraph,
            to_steps=project.get('option', 'to'),
            prune_nodes=project.get('option', 'prune')
        )
    except Exception as e:
        raise ValueError(f"Failed to construct runtime flowgraph: {e}")

    # --- Collect Overall Status ---
    record = project.get("record", field='schema')
    all_nodes = list(runtime_flow.get_nodes())
    node_statuses = {
        node: record.get("status", step=node[0], index=node[1])
        or NodeStatus.PENDING
        for node in all_nodes
    }

    succeeded = sum(1 for status in node_statuses.values() if status == NodeStatus.SUCCESS)
    failed = sum(1 for status in node_statuses.values() if status == NodeStatus.ERROR)
    skipped = sum(1 for status in node_statuses.values() if status == NodeStatus.SKIPPED)
    timeout = sum(1 for status in node_statuses.values() if status == NodeStatus.TIMEOUT)

    # Overall status determination
    if failed > 0 or timeout > 0:
        overall_status = "FAILED"
    elif succeeded + skipped == len(all_nodes):
        overall_status = "PASSED"
    else:
        overall_status = "INCOMPLETE"

    # --- Collect run header information ---
    headers_info = project._summary_headers()
    headers_info = [(title, value) for title, value in headers_info if title.lower() != "design"]
    headers_info = [
        ("overall status", overall_status),
        ("design", design),
        ("job name", jobname),
        ("flow", flow),
        *headers_info
    ]

    # filter out design
    max_header_title_len = max(len(title) for title, _ in headers_info)
    headers = [f"{title.title() if not title[0].isupper() else title:<{max_header_title_len}} : "
               f"{value}" for title, value in headers_info]

    # --- Collect Node Execution Table ---
    data = {}
    for step, index in all_nodes:
        status = node_statuses[(step, index)]
        tool, task, version = _get_task_info(project, flow, step, index)
        exit_code = record.get('toolexitcode', step=step, index=index)
        duration = _get_duration(project, step, index)

        data[(step, index)] = {
            'status': status,
            'tool': tool,
            'task': task,
            'version': version,
            'exit_code': _format_exit_code(exit_code),
            'duration': _format_duration(duration)
        }

    # --- Build Node Execution Table ---
    # Calculate column widths
    max_node_len = max(len(f"{s}/{i}") for s, i in all_nodes) if all_nodes else 10
    max_tool_len = max(len(info['tool']) for info in data.values()) if data else 10
    max_task_len = max(len(info['task']) for info in data.values()) if data else 10
    max_version_len = max(len(info['version']) if info['version'] else 0
                          for info in data.values()) if data else 10
    max_status_len = max(len(info['status']) if info['status'] else 0
                         for info in data.values()) if data else 10
    max_duration_len = max(len(info['duration']) if info['duration'] else 0
                           for info in data.values()) if data else 10

    col_node = max(max_node_len, 4)
    col_tool = max(max_tool_len, 4)
    col_task = max(max_task_len, 4)
    col_version = max(max_version_len, 7)
    col_status = max(max_status_len, 6)
    col_code = 4
    col_duration = max(max_duration_len, 8)
    col_warnings = 8
    col_errors = 6

    # Build table as list of lines
    table_lines = []

    # Header row
    node_header = (
        f"{'Node':<{col_node}} | "
        f"{'Tool':<{col_tool}} | "
        f"{'Task':<{col_task}} | "
        f"{'Version':<{col_version}} | "
        f"{'Status':<{col_status}} | "
        f"{'Exit':<{col_code}} | "
        f"{'Duration':<{col_duration}} | "
        f"{'Warnings':<{col_warnings}} | "
        f"{'Errors':<{col_errors}}"
    )
    table_lines.append(node_header)
    table_width = max(len(node_header), 80)

    table_lines.append("-" * table_width)

    # Node rows
    for node_level in flowgraph.get_execution_order():
        for step, index in node_level:
            node_name = f"{step}/{index}"
            status = node_statuses[(step, index)]

            # Get tool, task, and version
            tool, task, version = _get_task_info(project, flow, step, index)
            if version is None:
                version = "-"

            # Get exit code
            exit_code = record.get('toolexitcode', step=step, index=index)

            # Get duration
            duration = _get_duration(project, step, index)

            # Get key metrics (warnings and errors)
            warnings_str = "-"
            errors_str = "-"
            key_metrics = _get_node_key_metrics(project, step, index)
            if key_metrics:
                if 'warnings' in key_metrics:
                    warnings_str = str(key_metrics['warnings'])
                if 'errors' in key_metrics:
                    errors_str = str(key_metrics['errors'])

            row = (
                f"{node_name:<{col_node}} | "
                f"{tool:<{col_tool}} | "
                f"{task:<{col_task}} | "
                f"{version:^{col_version}} | "
                f"{status:<{col_status}} | "
                f"{_format_exit_code(exit_code):>{col_code}} | "
                f"{_format_duration(duration):>{col_duration}} | "
                f"{warnings_str:>{col_warnings}} | "
                f"{errors_str:>{col_errors}}"
            )
            table_lines.append(row)

    node_table = "\n".join(table_lines)

    # --- Collect Log File Paths ---
    log_files = []
    for node_level in flowgraph.get_execution_order():
        for step, index in node_level:
            logs = _get_log_paths(project, step, index)
            log = logs.get("exe", logs.get("sc", None))
            if log:
                node_str = f"{step}/{index}"
                rel_path = os.path.relpath(log, os.path.dirname(output_path))
                log_files.append(f"{node_str:>{max_node_len}} : {rel_path}")

    # --- Collect summary table information ---
    table = project.get("metric", field='schema').summary_table()
    if table.empty:
        metrics_table = "No metrics to display!"
    else:
        metrics_table = table.to_string(line_width=table_width, col_space=3)

    # --- Render Template ---
    template = get_file_template('report/end_of_run_summary.txt.j2')
    report_content = template.render(
        width=table_width,
        headers=headers,
        node_table=node_table,
        total_nodes=len(all_nodes),
        passed=succeeded,
        failed=failed,
        skipped=skipped,
        timeout=timeout,
        log_files=log_files,
        metrics_table=metrics_table,
        report_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        job_directory=jobdir(project),
        summary_file=output_path
    )

    # Write to file
    with open(output_path, 'w') as f:
        f.write(report_content)

    return output_path
