import os
import threading
import shutil
import fasteners
import logging

from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict

from rich.theme import Theme
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
from rich.console import Console
from rich.console import Group
from rich.padding import Padding

from siliconcompiler import SiliconCompilerError, NodeStatus
from siliconcompiler.report.dashboard import AbstractDashboard
from siliconcompiler.flowgraph import nodes_to_execute, _get_flowgraph_execution_order


class LogBufferHandler(logging.Handler):
    def __init__(self, n=50, event=None):
        """
        Initializes the handler.

        Args:
            n (int): Maximum number of lines to keep.
            event (threading.Event): Optional event to trigger on every log line.
        """
        super().__init__()
        self.buffer = deque(maxlen=n)
        self.event = event
        self._lock = threading.Lock()

    def emit(self, record):
        """
        Processes a log record.

        Args:
            record (logging.LogRecord): The log record to process.
        """
        log_entry = self.format(record)
        with self._lock:
            self.buffer.append(log_entry)
        if self.event:
            self.event.set()

    def get_lines(self):
        """
        Retrieves the last logged lines.

        Returns:
            list: A list of the last logged lines.
        """
        with self._lock:
            return list(self.buffer)


@dataclass
class JobData:
    total: int = 0
    success: int = 0
    error: int = 0
    finished: int = 0
    jobname: str = ""
    design: str = ""
    runtime: float = 0.0
    nodes: List[dict] = field(default_factory=list)


@dataclass
class SessionData:
    total: int = 0
    success: int = 0
    error: int = 0
    finished: int = 0
    runtime: float = 0.0
    jobs: Dict[str, JobData] = field(default_factory=dict)


class CliDashboard(AbstractDashboard):
    __status_color_map = {
        NodeStatus.PENDING: "blue",
        NodeStatus.QUEUED: "blue",
        NodeStatus.RUNNING: "orange4",
        NodeStatus.SUCCESS: "green",
        NodeStatus.ERROR: "red",
        NodeStatus.SKIPPED: "bright_black",
        NodeStatus.TIMEOUT: "red"
    }
    __theme = Theme(
        {
            # Text colors
            "text.primary": "white",
            "text.secondary": "cyan",
            # Background colors
            "background.primary": "grey15",
            "background.secondary": "dark_blue",
            # Highlight and accent colors
            "highlight": "green",
            "accent": " cyan",
            # Status colors
            "error": "red",
            "waring": "yellow",
            "success": "green",
            # Node status colors
            **{f"node.{status}": color for status, color in __status_color_map.items()},
            # Custom style for headers
            "header": "bold underline cyan",
        }
    )

    def __init__(self, chip):
        super().__init__(chip)

        self._lock = fasteners.InterProcessLock(self._manifest_lock)
        self._render_event = threading.Event()
        self._render_stop_event = threading.Event()
        self._render_thread = threading.Thread(target=self._render, daemon=True)

        self._render_data = SessionData()
        self._render_data_lock = threading.Lock()

        self.__console = Console(theme=CliDashboard.__theme)

        self.set_logger(chip.logger)

    def set_logger(self, logger):
        """
        Sets the logger for the dashboard.

        Args:
            logger (logging.Logger): The logger to set.
        """
        self._logger = logger
        if self._logger:
            self.__log_handler = LogBufferHandler(event=self._render_event)
            # Hijack the console
            self._logger.removeHandler(self._chip.logger._console)
            self._chip.logger._console = self.__log_handler
            self._logger.addHandler(self.__log_handler)

    def open_dashboard(self):
        """Starts the dashboard rendering thread if it is not already running."""

        if not self._render_thread.is_alive():
            self._update_render_data()
            self._render_thread.start()

    def update_manifest(self):
        """
        Updates the manifest file with the latest data from the chip object.
        This ensures that the dashboard reflects the current state of the chip.
        """
        if not self._manifest:
            return

        new_file = f"{self._manifest}.new.json"
        self._chip.write_manifest(new_file)

        with self._lock:
            shutil.move(new_file, self._manifest)

        self._update_render_data()
        self._render_event.set()

    def update_graph_manifests(self):
        """Placeholder method for updating graph manifests. Currently not implemented."""
        pass

    def is_running(self):
        """Returns True to indicate that the dashboard is running."""
        return True

    def end_of_run(self):
        """
        Stops the dashboard rendering thread and ensures all rendering operations are completed.
        """
        self.stop()

    def stop(self):
        """
        Stops the dashboard rendering thread and ensures all rendering operations are completed.
        """
        self._render_stop_event.set()
        self._render_event.set()
        # Wait for rendering to finish
        self._render_thread.join()

    def wait(self):
        """Waits for the dashboard rendering thread to finish."""
        self._render_thread.join()

    @staticmethod
    def format_status(status: str):
        """
        Formats the status of a node for display in the dashboard.

        Args:
            status (str): The status of the node (e.g., 'running', 'success', 'error').

        Returns:
            str: A formatted string with the status styled for display.
        """
        return f"[node.{status.lower()}]{status.upper()}[/]"

    @staticmethod
    def format_node(design, jobname, step, index) -> str:
        """
        Formats a node's information for display in the dashboard.

        Args:
            design (str): The design name.
            jobname (str): The job name.
            step (str): The step name.
            index (int): The step index.

        Returns:
            str: A formatted string with the node's information styled for display.
        """
        return f"{design}/{jobname}/{step}/{index}"

    def _render_log(self):
        if not self._logger:
            return Padding("")

        table = Table(box=None)
        table.add_column(overflow="crop", no_wrap=True)
        table.show_edge = False
        table.show_lines = False
        table.show_footer = False
        table.show_header = False
        for line in self.__log_handler.get_lines():
            table.add_row(f"[bright_black]{line}[/]")
        return table

    def _render_job_dashboard(self):
        """
        Creates a table of jobs and their statuses for display in the dashboard.

        Returns:
            Group: A Rich Group object containing tables for each job.
        """
        with self._render_data_lock:
            job_data = self._render_data.jobs.copy()  # Access jobs from SessionData

        if (
            self._render_data.finished > 0
            and self._render_data.total == self._render_data.finished
            and self._render_data.success == self._render_data.total
        ):
            return Padding("Done!")

        job_dashboards = []
        for jobname, job in job_data.items():
            table = Table(pad_edge=False)
            table.show_edge = False
            table.show_lines = False
            table.show_footer = False
            table.show_header = True
            table.add_column("Status")
            table.add_column("Node")
            table.add_column("Log")

            for node in job.nodes:
                if os.path.exists(node["log"]):
                    log_file = node["log"]
                else:
                    log_file = ""

                table.add_row(
                    CliDashboard.format_status(node["status"]),
                    CliDashboard.format_node(
                        job.design, job.jobname, node["step"], node["index"]
                    ),
                    (
                        log_file
                    )
                )

            job_dashboards.append(table)

        return Group(*job_dashboards)

    def _render_progress_bar(self):
        """
        Creates progress bars showing job completion for display in the dashboard.

        Returns:
            Group: A Rich Group object containing progress bars for each job.
        """
        with self._render_data_lock:
            job_data = self._render_data.jobs.copy()

        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            MofNCompleteColumn(),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        for _, job in job_data.items():
            progress.add_task(
                f"[text.primary]Progress ({job.design}/{job.jobname}):",
                total=job.total,
                completed=job.success,
            )

        return progress

    def _render_final(self):
        """
        Creates a summary of the final results, including runtime, passed, and failed jobs.

        Returns:
            Padding: A Rich Padding object containing the summary text.
        """
        with self._render_data_lock:
            success = self._render_data.success
            error = self._render_data.error
            total = self._render_data.total
            finished = self._render_data.finished
            runtime = self._render_data.runtime

        if finished != 0 and finished == total:
            return Padding(
                f"[text.primary]Results {runtime:.2f}s\n"
                f"     [success]{success} passed[/]\n"
                f"     [error]{error} failed[/]\n"
            )

        return Group(Padding("", (0, 0)), self._render_log())

    def _render(self):
        """
        Main rendering method for the TUI. Continuously updates the dashboard
        with the latest data until the stop event is set.
        """
        live = None
        try:
            live = Live(
                self._get_rendable(),
                console=self.__console,
                screen=False,
                transient=True,
                auto_refresh=False,
            )
            live.start()

            while not self._render_stop_event.is_set():
                self._render_event.wait()
                self._render_event.clear()

                if self._render_stop_event.is_set():
                    break

                live.update(self._get_rendable(), refresh=True)
        finally:
            try:
                if live:
                    live.stop()
                    self.__console.print(self._get_rendable())
            finally:
                # Restore the prompt
                print("\033[?25h", end="")

    def _get_rendable(self):
        """
        Combines all dashboard components (job table, progress bars, final summary)
        into a single renderable group.

        Returns:
            Group: A Rich Group object containing all dashboard components.
        """
        new_table = self._render_job_dashboard()
        new_bar = self._render_progress_bar()
        finished = self._render_final()

        panel_group = Group(
            Padding("", (0, 0)),
            new_table,
            Padding("", (0, 0)),
            new_bar,
            Padding("", (0, 0)),
            finished,
        )

        return panel_group

    def _update_render_data(self):
        """
        Updates the render data with the latest job and node information from the chip object.
        This data is used to populate the dashboard.
        """

        job_data = self._get_job()

        with self._render_data_lock:
            self._render_data.jobs[self._chip] = job_data
            self._render_data.total = sum(
                job.total for job in self._render_data.jobs.values()
            )
            self._render_data.success = sum(
                job.success for job in self._render_data.jobs.values()
            )
            self._render_data.error = sum(
                job.error for job in self._render_data.jobs.values()
            )
            self._render_data.finished = sum(
                job.finished for job in self._render_data.jobs.values()
            )
            self._render_data.runtime = max(
                job.runtime for job in self._render_data.jobs.values()
            )

    def _get_job(self, chip=None) -> JobData:
        chip = chip or self._chip

        nodes = []
        try:
            flow = chip.get('option', 'flow')
            if not flow:
                raise SiliconCompilerError("dummy error")
            execnodes = nodes_to_execute(chip)
            for nodeset in _get_flowgraph_execution_order(chip, flow):
                for node in nodeset:
                    if node not in execnodes:
                        continue
                    nodes.append(node)
        except SiliconCompilerError:
            pass

        design = chip.get("design")
        jobname = chip.get("option", "jobname")

        job_data = JobData()
        job_data.jobname = jobname
        job_data.design = design
        totaltimes = [
                self._chip.get("metric", "totaltime", step=step, index=index) or 0
                for step, index in nodes
            ]
        if not totaltimes:
            totaltimes = [0]
        job_data.runtime = max(totaltimes)

        for step, index in nodes:
            status = self._chip.get("record", "status", step=step, index=index)
            if not status:
                status = NodeStatus.PENDING

            job_data.total += 1
            if NodeStatus.is_error(status):
                job_data.error += 1
            if NodeStatus.is_success(status):
                job_data.success += 1
            if NodeStatus.is_done(status):
                job_data.finished += 1

            if status == NodeStatus.SKIPPED:
                continue

            job_data.nodes.append(
                {
                    "step": step,
                    "index": index,
                    "status": status,
                    "log": os.path.join(
                        os.path.relpath(
                            self._chip.getworkdir(step=step, index=index),
                            self._chip.cwd,
                        ),
                        f"{step}.log",
                    ),
                })

        return job_data
