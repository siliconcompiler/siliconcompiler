import os
import threading
import logging
import queue
import time
import multiprocessing

from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict

from rich import box
from rich.theme import Theme
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
from rich.console import Console
from rich.console import Group
from rich.padding import Padding

from siliconcompiler import SiliconCompilerError, NodeStatus
from siliconcompiler.utils.logging import SCColorLoggerFormatter
from siliconcompiler.flowgraph import RuntimeFlowgraph

import atexit


class LogBufferHandler(logging.Handler):
    def __init__(self, sync_queue, n=50, event=None):
        """
        Initializes the handler.

        Args:
            n (int): Maximum number of lines to keep.
            event (threading.Event): Optional event to trigger on every log line.
        """
        super().__init__()
        self.queue = sync_queue
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
        log_entry = log_entry.replace("[", "\\[")

        # Replace console coloring
        for color, replacement in (
                (SCColorLoggerFormatter.reset.replace("[", "\\["), "[/]"),
                (SCColorLoggerFormatter.blue.replace("[", "\\["), "[blue]"),
                (SCColorLoggerFormatter.yellow.replace("[", "\\["), "[yellow]"),
                (SCColorLoggerFormatter.red.replace("[", "\\["), "[red]"),
                (SCColorLoggerFormatter.bold_red.replace("[", "\\["), "[bold red]")):
            log_entry = log_entry.replace(color, replacement)
        self.queue.put(log_entry)
        if self.event:
            self.event.set()

    def get_lines(self, lines=None):
        """
        Retrieves the last logged lines.

        Returns:
            list: A list of the last logged lines.
        """
        with self._lock:
            while not self.queue.empty():
                try:
                    self.buffer.append(self.queue.get_nowait())
                except queue.Empty:
                    break
            buffer_list = list(self.buffer)
            if lines is None or lines > len(buffer_list):
                return buffer_list
            return buffer_list[-lines:]


@dataclass
class JobData:
    total: int = 0
    success: int = 0
    error: int = 0
    skipped: int = 0
    finished: int = 0
    jobname: str = ""
    design: str = ""
    runtime: float = 0.0
    complete: bool = False
    nodes: List[dict] = field(default_factory=list)


@dataclass
class SessionData:
    total: int = 0
    success: int = 0
    error: int = 0
    skipped: int = 0
    finished: int = 0
    runtime: float = 0.0
    jobs: Dict[str, JobData] = field(default_factory=dict)


@dataclass
class Layout:
    """
    Layout class represents the configuration for a dashboard layout.

    Attributes:
        height (int): The total height of the layout.
        width (int): The total width of the layout.
        job_board_min (int): The minimum height allocated for the job board.
        job_board_max (int): The maximum height allocated for the job board.
        log_max (int): The maximum height allocated for the log section.
        log_min (int): The minimum height allocated for the log section.
        progress_bar_min (int): The minimum height allocated for the progress bar.
        progress_bar_max (int): The maximum height allocated for the progress bar.
        job_board_show_log (bool): A flag indicating whether to show the log in the job board.

        __reserved (int): Reserved space for table headings and extra padding.

    Methods:
        available_height():
            Calculates and returns the available height for other components in the layout
            after accounting for reserved space, job board, and log sections.
            Returns 0 if the total height is not set.
    """

    height: int = 0
    width: int = 0

    log_height = 0
    job_board_height = 0
    progress_bar_height = 0

    job_board_show_log: bool = True
    job_board_v_limit: int = 120

    __progress_bar_height_default = 1
    padding_log = 2
    padding_progress_bar = 1
    padding_job_board = 1
    padding_job_board_header = 1

    def update(self, height, width, visible_jobs, visible_bars):
        self.height = height
        self.width = width

        min_required = (
            max(visible_bars, self.__progress_bar_height_default)
            + self.padding_progress_bar
        )
        if self.height < min_required:
            self.progress_bar_height = 0
            self.job_board_height = 0
            self.log_height = 0
            return

        remaining_height = self.height

        # Allocate progress bar space (highest priority)
        self.progress_bar_height = max(visible_bars, self.__progress_bar_height_default)
        if self.progress_bar_height > 0:
            remaining_height -= self.progress_bar_height + self.padding_progress_bar

        # Calculate job board requirements
        job_board_min_space = self.padding_job_board_header + self.padding_job_board
        job_board_max_nodes = remaining_height // 2
        visible_jobs = min(visible_jobs, job_board_max_nodes)
        if visible_jobs > 0:
            job_board_full_space = visible_jobs + job_board_min_space
        else:
            job_board_full_space = 0

        # Allocate job board space (second priority)
        if remaining_height <= job_board_min_space:
            self.job_board_height = 0
            self.log_height = 0
        elif remaining_height <= job_board_full_space:
            self.job_board_height = remaining_height - job_board_min_space
            self.log_height = 0
        elif visible_jobs == 0:
            self.job_board_height = 0
            self.log_height = remaining_height
        else:
            self.job_board_height = visible_jobs
            self.log_height = remaining_height - job_board_full_space - self.padding_log

        if self.width < self.job_board_v_limit:
            self.job_board_show_log = False


class BoardSingleton(type):
    _instances = {}
    _lock = multiprocessing.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(BoardSingleton, cls).__call__(*args, **kwargs)
                cls._instances[cls]._init_singleton()
        return cls._instances[cls]


class Board(metaclass=BoardSingleton):
    __status_color_map = {
        NodeStatus.PENDING: "blue",
        NodeStatus.QUEUED: "blue",
        NodeStatus.RUNNING: "orange4",
        NodeStatus.SUCCESS: "green",
        NodeStatus.ERROR: "red",
        NodeStatus.SKIPPED: "bright_black",
        NodeStatus.TIMEOUT: "red",
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
            "warning": "yellow",
            "success": "green",
            # Node status colors
            **{f"node.{status}": color for status, color in __status_color_map.items()},
            # Custom style for headers
            "header": "bold underline cyan",
        }
    )

    __JOB_BOARD_HEADER = True

    __JOB_BOARD_BOX = box.SIMPLE_HEAD

    def __init__(self):
        pass

    def _init_singleton(self):
        self._console = Console(theme=Board.__theme)

        self.live = Live(
            console=self._console,
            screen=False,
            auto_refresh=True,
        )

        atexit.register(self._stop_on_exit)

        self._active = self._console.is_terminal
        if not self._active:
            self._console = None
            return

        self._layout = Layout()

        # Manager to thread data
        self._manager = multiprocessing.Manager()

        self._render_event = self._manager.Event()
        self._render_stop_event = self._manager.Event()
        self._render_thread = None

        # Holds thread job data
        self._board_info = self._manager.Namespace()
        self._board_info.data_modified = False
        self._job_data = self._manager.dict()
        self._job_data_lock = self._manager.Lock()

        self._render_data = SessionData()
        self._render_data_lock = threading.Lock()

        self._log_handler_queue = self._manager.Queue()

        self._log_handler = LogBufferHandler(
            self._log_handler_queue, n=120, event=self._render_event)

        if not self.__JOB_BOARD_HEADER:
            self._layout.padding_job_board_header = 0

        self._metrics = ("warnings", "errors")

    def _stop_on_exit(self):
        self.stop()

    def open_dashboard(self):
        """Starts the dashboard rendering thread if it is not already running."""

        if not self._active:
            return

        if not self.is_running():
            self._update_render_data(None)

            with self._job_data_lock:
                if not self._render_thread or not self._render_thread.is_alive():
                    self._render_thread = threading.Thread(target=self._render, daemon=True)
                    self._render_event.clear()
                    self._render_stop_event.clear()

                    self._render_thread.start()

    def update_manifest(self, chip, starttimes=None):
        """
        Updates the manifest file with the latest data from the chip object.
        This ensures that the dashboard reflects the current state of the chip.
        """

        if not self._active:
            return

        self._update_render_data(chip, starttimes=starttimes)

    def is_running(self):
        """Returns True to indicate that the dashboard is running."""

        if not self._active:
            return False

        with self._job_data_lock:
            if not self._render_thread:
                return False

            return self._render_thread.is_alive()

    def end_of_run(self, chip):
        """
        Stops the dashboard rendering thread and ensures all rendering operations are completed.
        """

        if not self._active:
            return

        self._update_render_data(chip, complete=True)

    def stop(self):
        """
        Stops the dashboard rendering thread and ensures all rendering operations are completed.
        """
        if not self.is_running():
            return

        if self._job_data:
            if any([not job.complete for job in self._job_data.values()]):
                return

        self._render_stop_event.set()
        self._render_event.set()

        # Wait for rendering to finish
        self.wait()

        # Restore terminal
        self.live.stop()
        self._console.show_cursor()

    def wait(self):
        """Waits for the dashboard rendering thread to finish."""
        if not self.is_running():
            return

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
    def format_node(design, jobname, step, index, multi_job) -> str:
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
        if multi_job:
            return f"{design}/{jobname}/{step}/{index}"
        else:
            return f"{step}/{index}"

    def _render_log(self, layout):
        if layout.log_height == 0:
            return None

        table = Table(box=None)
        table.add_column(overflow="ellipsis", no_wrap=True, vertical="bottom")
        table.show_edge = False
        table.show_lines = False
        table.show_footer = False
        table.show_header = False
        for line in self._log_handler.get_lines(layout.log_height):
            table.add_row(f"[bright_black]{line}[/]")
        while table.row_count < layout.log_height:
            table.add_row("")

        return Group(table, Padding("", (0, 0)))

    def _render_job_dashboard(self, layout):
        """
        Creates a table of jobs and their statuses for display in the dashboard.

        Returns:
            Group: A Rich Group object containing tables for each job.
        """
        # Don't render anything if there is not enough space
        if layout.job_board_height == 0:
            return None

        with self._render_data_lock:
            job_data = self._render_data.jobs.copy()  # Access jobs from SessionData

        if self.__JOB_BOARD_HEADER:
            table_box = self.__JOB_BOARD_BOX
        else:
            table_box = None

        table = Table(box=table_box, pad_edge=False)
        table.show_edge = False
        table.show_lines = False
        table.show_footer = False
        table.show_header = self.__JOB_BOARD_HEADER
        table.add_column("Status")
        table.add_column("Node")
        table.add_column("Time", justify="right")
        for metric in self._metrics:
            table.add_column(metric.capitalize(), justify="right")
        if layout.job_board_show_log:
            table.add_column("Log")

        multi_jobs = len(job_data) > 1 or True

        # jobname, node index, priority, node order
        table_data_select = []
        for chipid, job in job_data.items():
            for n, node in enumerate(job.nodes):
                table_data_select.append(
                    (chipid, n, node["print"]["priority"], node["print"]["order"])
                )

        # sort for priority
        table_data_select = sorted(table_data_select, key=lambda d: (d[2], *d[3], d[0]))

        # trim to size
        table_data_select = table_data_select[0:layout.job_board_height]

        # sort for printing order
        table_data_select = sorted(table_data_select, key=lambda d: (d[0], *d[3], d[2]))

        table_data = []

        for chipid, node_idx, _, _ in table_data_select:
            job = job_data[chipid]
            node = job.nodes[node_idx]

            if (
                layout.job_board_show_log
                and os.path.exists(node["log"])
            ):
                log_file = "[bright_black]{}[/]".format(node['log'])
            else:
                log_file = None

            if node["time"]["duration"] is not None:
                duration = f'{node["time"]["duration"]:.1f}s'
            elif node["time"]["start"] is not None:
                duration = f'{time.time() - node["time"]["start"]:.1f}s'
            else:
                duration = ""

            table_data.append((
                Board.format_status(node["status"]),
                Board.format_node(
                    job.design, job.jobname, node["step"], node["index"],
                    multi_jobs
                ),
                duration,
                *node["metrics"],
                log_file
            ))

        for row_data in table_data:
            table.add_row(*row_data)

        if table.row_count == 0:
            return None

        if self.__JOB_BOARD_HEADER:
            return Group(table, Padding("", (0, 0)))
        return Group(Padding("", (0, 0)), table, Padding("", (0, 0)))

    def _render_progress_bar(self, layout):
        """
        Creates progress bars showing job completion for display in the dashboard.

        Returns:
            Group: A Rich Group object containing progress bars for each job.
        """
        with self._render_data_lock:
            job_data = self._render_data.jobs.copy()
            done = self._render_data.finished > 0 \
                and self._render_data.total == self._render_data.finished \
                and self._render_data.success == self._render_data.total

        if done:
            return None

        ref_time = time.time()
        runtimes = {}
        for name, job in job_data.items():
            if job.complete:
                runtimes[name] = job.runtime
            else:
                runtime = 0.0
                for node in job.nodes:
                    if node["time"]["duration"] is not None:
                        runtime += node["time"]["duration"]
                    elif node["time"]["start"] is not None:
                        runtime += ref_time - node["time"]["start"]
                runtimes[name] = runtime

        runtime_width = len(f"{max([0, *runtimes.values()]):.1f}")

        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            MofNCompleteColumn(),
            BarColumn(bar_width=60),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn(f" {{task.fields[runtime]:>{runtime_width}.1f}}s")
        )
        nodes = 0
        for name, job in job_data.items():
            nodes += len(job.nodes)
            progress.add_task(
                f"[text.primary]Progress ({job.design}/{job.jobname}):",
                total=job.total,
                completed=job.success,
                runtime=runtimes[name]
            )

        if nodes == 0:
            return Padding("", (0, 0))

        return Group(progress, Padding("", (0, 0)))

    def _render_final(self, layout):
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

        return self._render_log(layout)

    def _render(self):
        """
        Main rendering method for the TUI. Continuously updates the dashboard
        with the latest data until the stop event is set.
        """

        def update_data():
            try:
                self._update_rendable_data()
            except:  # noqa E722
                # Catch any multiprocessing errors
                pass

        def check_stop_event():
            try:
                return self._render_stop_event.is_set()
            except:  # noqa E722
                # Catch any multiprocessing errors
                return True

        try:
            update_data()

            if not self.live.is_started:
                self.live.start(refresh=True)

            while not check_stop_event():
                try:
                    if self._render_event.wait(timeout=0.2):
                        self._render_event.clear()
                except:  # noqa E722
                    # Catch any multiprocessing errors
                    break

                if check_stop_event():
                    break

                update_data()
                self.live.update(self._get_rendable(), refresh=True)

        finally:
            update_data()
            if self.live:
                self.live.update(self._get_rendable(), refresh=True)
            else:
                self._console.print(self._get_rendable())

    def _update_layout(self):
        with self._render_data_lock:
            visible_progress_bars = len(self._render_data.jobs)
            visible_jobs_count = self._render_data.total - self._render_data.skipped

        self._layout.update(
            self._console.height,
            self._console.width,
            visible_jobs_count,
            visible_progress_bars,
        )

        return self._layout

    def _update_rendable_data(self):
        jobs = {}
        with self._job_data_lock:
            if self._board_info.data_modified:
                self._board_info.data_modified = False
                for job, data in self._job_data.items():
                    jobs[job] = data

        if not jobs:
            return

        with self._render_data_lock:
            self._render_data.jobs.clear()
            for job, data in jobs.items():
                self._render_data.jobs[job] = data

            self._render_data.total = sum(
                [0, *[job.total for job in self._render_data.jobs.values()]]
            )
            self._render_data.success = sum(
                [0, *[job.success for job in self._render_data.jobs.values()]]
            )
            self._render_data.error = sum(
                [0, *[job.error for job in self._render_data.jobs.values()]]
            )
            self._render_data.skipped = sum(
                [0, *[job.skipped for job in self._render_data.jobs.values()]]
            )
            self._render_data.finished = sum(
                [0, *[job.finished for job in self._render_data.jobs.values()]]
            )
            self._render_data.runtime = max(
                [0, *[job.runtime for job in self._render_data.jobs.values()]]
            )

    def _get_rendable(self):
        """
        Combines all dashboard components (job table, progress bars, final summary)
        into a single renderable group.

        Returns:
            Group: A Rich Group object containing all dashboard components.
        """

        layout = self._update_layout()

        new_table = self._render_job_dashboard(layout)
        new_bar = self._render_progress_bar(layout)
        footer = self._render_final(layout)

        items = []
        if new_table:
            items.extend([new_table])

        if new_bar:
            items.extend([new_bar])

        if footer:
            items.extend([footer])

        return Group(*items)

    def _update_render_data(self, chip, starttimes=None, complete=False):
        """
        Updates the render data with the latest job and node information from the chip object.
        This data is used to populate the dashboard.
        """

        if not chip:
            return

        job_data = self._get_job(chip, starttimes=starttimes)
        job_data.complete = complete

        if not job_data.nodes:
            return

        chip_id = f"{job_data.design}/{job_data.jobname}"
        with self._job_data_lock:
            self._job_data[chip_id] = job_data
            self._board_info.data_modified = True
            self._render_event.set()

    def _get_job(self, chip, starttimes=None) -> JobData:
        if not starttimes:
            starttimes = {}

        nodes = []
        nodestatus = {}
        nodeorder = {}
        node_priority = {}
        try:
            node_inputs = {}
            node_outputs = {}
            flow = chip.get("option", "flow")
            if not flow:
                raise SiliconCompilerError("dummy error")

            runtime_flow = RuntimeFlowgraph(
                chip.schema.get("flowgraph", flow, field='schema'),
                to_steps=chip.get('option', 'to'),
                prune_nodes=chip.get('option', 'prune'))
            record = chip.schema.get("record", field='schema')

            execnodes = runtime_flow.get_nodes()
            lowest_priority = 3 * len(execnodes)  # 2x + 1 is lowest computed, so 3x will be lower
            for n, nodeset in enumerate(runtime_flow.get_execution_order()):
                for m, node in enumerate(nodeset):
                    if node not in execnodes:
                        continue
                    nodes.append(node)

                    node_priority[node] = lowest_priority

                    status = chip.get("record", "status", step=node[0], index=node[1])
                    if status is None:
                        status = NodeStatus.PENDING
                    nodestatus[node] = status
                    nodeorder[node] = (n, m)

                    node_inputs[node] = runtime_flow.get_node_inputs(*node, record=record)
                    for in_node in chip.get('flowgraph', flow, node[0], node[1], 'input'):
                        node_outputs.setdefault(in_node, set()).add(node)

            flow_entry_nodes = set(
                chip.schema.get("flowgraph", flow, field="schema").get_entry_nodes())

            running_nodes = set([node for node in nodes if NodeStatus.is_running(nodestatus[node])])
            done_nodes = set([node for node in nodes if NodeStatus.is_done(nodestatus[node])])
            error_nodes = set([node for node in nodes if NodeStatus.is_error(nodestatus[node])])

            def get_node_distance(node, search, level=1):
                dists = {}

                if node not in search:
                    return dists

                for snode in search[node]:
                    dists[snode] = level
                    dists.update(get_node_distance(snode, search, level=level+1))

                return dists

            # Compute relative node distances
            node_dists = {}
            for cnode in nodes:
                # use 2x + 1 to give completed nodes sorting priority
                node_dists[cnode] = {
                    node: 2*level+1 for node, level in get_node_distance(cnode, node_inputs).items()
                }
                node_dists[cnode].update({
                    node: 2*level for node, level in get_node_distance(cnode, node_outputs).items()
                })

            # Compute printing priority of nodes
            remaining_entry_nodes = flow_entry_nodes - done_nodes
            startnodes = running_nodes.union(remaining_entry_nodes)
            priority_node = {0: startnodes.union(error_nodes)}
            for node in nodes:
                dists = node_dists[node]
                levels = []
                for snode in startnodes:
                    if snode not in dists:
                        continue
                    levels.append(dists[snode])
                if not levels:
                    continue
                priority_node.setdefault(min(levels), set()).add(node)
            for level, level_nodes in priority_node.items():
                for node in level_nodes:
                    if node not in node_priority:
                        continue
                    node_priority[node] = min(node_priority[node], level)
        except SiliconCompilerError:
            pass

        design = chip.get("design")
        jobname = chip.get("option", "jobname")

        job_data = JobData()
        job_data.jobname = jobname
        job_data.design = design
        totaltimes = [
            chip.get("metric", "totaltime", step=step, index=index) or 0
            for step, index in nodes
        ]
        if not totaltimes:
            totaltimes = [0]
        job_data.runtime = max(totaltimes)

        for step, index in nodes:
            status = nodestatus[(step, index)]

            job_data.total += 1
            if NodeStatus.is_error(status):
                job_data.error += 1
            if NodeStatus.is_success(status):
                job_data.success += 1
            if NodeStatus.is_done(status):
                job_data.finished += 1

            if status == NodeStatus.SKIPPED:
                job_data.skipped += 1
                continue

            starttime = None
            duration = None
            if NodeStatus.is_done(status):
                duration = chip.get("metric", "tasktime", step=step, index=index)
            if (step, index) in starttimes:
                starttime = starttimes[(step, index)]

            node_metrics = []
            for metric in self._metrics:
                value = chip.get('metric', metric, step=step, index=index)
                if value is None:
                    node_metrics.append("")
                else:
                    node_metrics.append(str(value))

            job_data.nodes.append(
                {
                    "step": step,
                    "index": index,
                    "status": status,
                    "time": {
                        "start": starttime,
                        "duration": duration
                    },
                    "metrics": node_metrics,
                    "log": os.path.join(
                        os.path.relpath(
                            chip.getworkdir(step=step, index=index),
                            chip.cwd,
                        ),
                        f"{step}.log",
                    ),
                    "print": {
                        "order": nodeorder[(step, index)],
                        "priority": node_priority[(step, index)]
                    }
                }
            )

        return job_data
