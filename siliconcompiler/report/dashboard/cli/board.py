import logging
import os
import math
import queue
import re
import time
import threading

import os.path

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict

from rich import box
from rich.theme import Theme
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
from rich.console import Console
from rich.console import Group
from rich.padding import Padding

from siliconcompiler import NodeStatus
from siliconcompiler.utils.logging import SCColorLoggerFormatter
from siliconcompiler.utils.paths import workdir
from siliconcompiler.flowgraph import RuntimeFlowgraph


class LogBuffer:
    """
    A buffer for storing log messages, designed to be thread-safe and to work
    in conjunction with a `LogBufferHandler` for dashboard or UI display.
    It uses a `collections.deque` to maintain a fixed-size history of log lines.
    """
    def __init__(self, queue: queue.Queue, n: int = 15, event: threading.Event = None):
        """
        Initializes the LogBuffer.

        Args:
            queue (queue.Queue): A thread-safe queue to push new log lines to.
            n (int): The maximum number of log lines to retain in the buffer's history.
                     Defaults to 15.
            event (threading.Event, optional): An optional `threading.Event` object.
                                             If provided, this event is set whenever
                                             a new log line is added, signaling
                                             consumers that new data is available.
                                             Defaults to None.
        """
        self.queue = queue
        self.buffer = deque(maxlen=n)
        self.lock = threading.Lock()
        if not event:
            # Create dummy event
            event = threading.Event()
        self.event = event

    def make_handler(self, logger_unicode_map) -> logging.Handler:
        """
        Creates and returns a `LogBufferHandler` instance associated with this `LogBuffer`.

        This handler can then be added to a Python logger to direct log messages
        to this buffer.

        Returns:
            logging.Handler: An instance of `LogBufferHandler`.
        """
        return LogBufferHandler(self, logger_unicode_map)

    def add_line(self, line: str):
        """
        Adds a new log line to the internal queue and signals the event.

        This method is called by the `LogBufferHandler` (or directly) to
        append a processed log line to the buffer. It also sets the internal
        threading event to notify any waiting consumers.

        Args:
            line (str): The log line (string) to add.
        """
        self.queue.put(line)
        self.event.set()

    def get_lines(self, lines: int = None) -> List[str]:
        """
        Retrieves the last logged lines from the buffer.

        New lines are first moved from the internal queue to the buffer,
        and then the requested number of lines are returned from the buffer's history.

        Args:
            lines (int, optional): The maximum number of recent lines to retrieve.
                                   If None, all lines currently in the buffer are returned.
                                   Defaults to None.

        Returns:
            list[str]: A list of the last logged lines.
        """
        new_lines = []
        try:
            for _ in range(self.queue.qsize()):
                new_lines.append(self.queue.get_nowait())
        except queue.Empty:
            pass
        if not self.queue.empty():
            # Set event since queue is not empty
            self.event.set()

        with self.lock:
            self.buffer.extend(new_lines)
            buffer_list = list(self.buffer)

            if lines is None or lines > len(buffer_list):
                return buffer_list
            return buffer_list[-lines:]


class LogBufferHandler(logging.Handler):
    """
    A custom logging handler that buffers log records and processes them
    for display in a dashboard or other UI, replacing console color codes
    with a simplified markdown-like format.
    """
    def __init__(self, parent: LogBuffer, logger_unicode_map):
        """
        Initializes the LogBufferHandler.

        Args:
            parent (LogBuffer): The parent `LogBuffer` instance to which processed
                                log lines will be added.
        """
        super().__init__()
        self._parent = parent

        self.__logger_unicode_map = logger_unicode_map
        if self.__logger_unicode_map:
            self.__logger_unicode_map = self.__logger_unicode_map.copy()
            for key, value in self.__logger_unicode_map.items():
                self.__logger_unicode_map[key] = f"| {value}  |"
            self.__unicode_rep = re.compile(r"^\|\s[\u001ba-zA-Z0-9\[\\ ]+\s+\|")
        else:
            self.__unicode_rep = None

    def emit(self, record):
        """
        Processes a log record, formats it, replaces console color codes,
        and adds the transformed line to the parent `LogBuffer`.

        Args:
            record (logging.LogRecord): The log record to process.
        """
        log_entry = self.format(record)
        if self.__unicode_rep:
            log_entry = self.__unicode_rep.sub(
                self.__logger_unicode_map.get(record.levelname, record.levelname), log_entry)
        else:
            log_entry = log_entry.replace("[", "\\[")

            # Replace console coloring
            for color, replacement in (
                    (SCColorLoggerFormatter.reset.replace("[", "\\["), "[/]"),
                    (SCColorLoggerFormatter.blue.replace("[", "\\["), "[blue]"),
                    (SCColorLoggerFormatter.yellow.replace("[", "\\["), "[yellow]"),
                    (SCColorLoggerFormatter.red.replace("[", "\\["), "[red]"),
                    (SCColorLoggerFormatter.bold_red.replace("[", "\\["), "[bold red]")):
                log_entry = log_entry.replace(color, replacement)
        self._parent.add_line(log_entry)


@dataclass
class JobData:
    """
    A data class to hold information about a single job's progress and status.

    Attributes:
        total (int): The total number of nodes in the job.
        success (int): The number of successfully completed nodes.
        error (int): The number of nodes that resulted in an error.
        skipped (int): The number of skipped nodes.
        finished (int): The total number of finished nodes (success or error).
        jobname (str): The name of the job.
        design (str): The name of the design associated with the job.
        runtime (float): The total runtime of the job so far.
        complete (bool): A flag indicating if the job has completed.
        nodes (List[dict]): A list of dictionaries, each containing detailed
                            information about a single node in the flowgraph.
    """
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
    """
    A data class to hold aggregated information about the entire run session,
    which may include multiple jobs.

    Attributes:
        total (int): The total number of nodes across all jobs.
        success (int): The total number of successfully completed nodes across all jobs.
        error (int): The total number of nodes that resulted in an error across all jobs.
        skipped (int): The total number of skipped nodes across all jobs.
        finished (int): The total number of finished nodes across all jobs.
        runtime (float): The maximum runtime among all jobs.
        jobs (Dict[str, JobData]): A dictionary mapping job identifiers to their
                                   corresponding JobData objects.
    """
    total: int = 0
    success: int = 0
    error: int = 0
    skipped: int = 0
    finished: int = 0
    runtime: float = 0.0
    jobs: Dict[str, JobData] = field(default_factory=dict)


class NodeType(Enum):
    """Enumeration to categorize flowgraph nodes as entry, exit, or other."""
    ENTRY = "entry"
    EXIT = "exit"
    OTHER = "other"


@dataclass
class Layout:
    """
    Manages the dynamic layout of the dashboard, calculating the height
    of different sections based on terminal size and content.

    Attributes:
        height (int): The total height of the terminal.
        width (int): The total width of the terminal.
        log_height (int): The calculated height for the log display area.
        job_board_height (int): The calculated height for the job status board.
        progress_bar_height (int): The calculated height for the progress bar section.
        job_board_show_log (bool): Flag to determine if the log file column is shown.
        job_board_v_limit (int): Width threshold to switch to a more compact view.
    """

    height: int = 0
    width: int = 0

    log_height: int = 0
    job_board_height: int = 0
    progress_bar_height: int = 0

    job_board_show_log: bool = True
    job_board_v_limit: int = 120

    __progress_bar_height_default = 1
    padding_log = 2
    padding_progress_bar: int = 1
    padding_job_board: int = 1
    padding_job_board_header: int = 1

    show_node_type: bool = False

    def update(self, height: int, width: int, visible_jobs: int, visible_bars: int):
        """
        Recalculates the layout dimensions based on the current terminal size and content.

        This method implements the logic to intelligently allocate vertical space
        to the progress bars, job board, and log view.

        Args:
            height (int): The current terminal height.
            width (int): The current terminal width.
            visible_jobs (int): The number of job nodes to be displayed.
            visible_bars (int): The number of progress bars to be displayed.
        """
        self.height = height
        self.width = width

        if self.height < 3:
            self.progress_bar_height = self.height - self.padding_progress_bar - 1
            self.job_board_height = 0
            self.log_height = 0

        # target sizes
        target_jobs = 0.25 * self.height
        target_bars = 0.50 * self.height
        # 25 % for log

        # Adjust targets based on progress bars
        if visible_bars < target_bars:
            remainder = target_bars - visible_bars
            target_bars = visible_bars
            target_jobs += 0.75 * remainder
        target_bars = int(math.ceil(target_bars))

        # Adjust targets based on jobs
        if visible_jobs < target_jobs:
            target_jobs = visible_jobs
        target_jobs = int(math.ceil(target_jobs))

        remaining_height = self.height

        # Allocate progress bar space (highest priority)
        self.progress_bar_height = max(min(target_bars, visible_bars),
                                       self.__progress_bar_height_default)
        if self.progress_bar_height > 0:
            remaining_height -= self.progress_bar_height + self.padding_progress_bar

        # Calculate job board requirements
        job_board_min_space = self.padding_job_board_header + self.padding_job_board
        job_board_max_nodes = remaining_height // 2
        visible_jobs = min(min(target_jobs, visible_jobs), job_board_max_nodes)
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
        if self.log_height < 0:
            self.log_height = 0

        if self.width < self.job_board_v_limit:
            self.job_board_show_log = False


class Board:
    """
    The main class for rendering the live dashboard UI.

    This class orchestrates the display of job progress, logs, and status updates
    in the terminal using the `rich` library. It runs in a separate thread to
    provide a non-blocking UI.
    """
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
    _symbols = {
        "table": {
            "warnings": "⚠️",
            "errors": "🚫",
            "time": "⏳",
            "log": "📜",
        },
        "logging": {
            logging.getLevelName(logging.DEBUG): "🐛",
            logging.getLevelName(logging.INFO): "ℹ️",
            logging.getLevelName(logging.WARNING): "⚠️",
            logging.getLevelName(logging.ERROR): "🚫",
            logging.getLevelName(logging.CRITICAL): "🚨"
        },
        "node": {
            NodeType.ENTRY: "🏠",
            NodeType.EXIT: "🎯"
        }
    }

    __USE_ICONS = False

    __JOB_BOARD_HEADER = True

    __JOB_BOARD_BOX = box.SIMPLE_HEAD

    def __init__(self, manager):
        """
        Initializes the Board.

        Args:
            manager: A multiprocessing.Manager object to create shared state
                     (events, dicts, locks) between processes.
        """
        self._console = Console(theme=Board.__theme)

        self.live = Live(
            console=self._console,
            screen=True,
            auto_refresh=True
        )

        self._active = self._console.is_terminal
        if not self._active:
            self._console = None
            return

        self._layout = Layout()

        if Board.__USE_ICONS:
            self._layout.show_node_type = True
        else:
            Board._symbols.clear()

        self._render_event = manager.Event()
        self._render_stop_event = manager.Event()
        self._render_thread = None

        # Holds thread job data
        self._board_info = manager.Namespace()
        self._board_info.data_modified = False
        self._job_data = manager.dict()
        self._job_data_lock = manager.Lock()

        self._render_data = SessionData()
        self._render_data_lock = threading.Lock()

        self._log_handler_queue = manager.Queue()

        self._log_handler = LogBuffer(self._log_handler_queue, n=120, event=self._render_event)

        # Sleep time for the dashboard
        self._dwell = 0.1

        if not self.__JOB_BOARD_HEADER:
            self._layout.padding_job_board_header = 0

        self._metrics = ("warnings", "errors")

    def make_log_hander(self) -> logging.Handler:
        """
        Creates and returns a logging handler that directs logs to this board.

        Returns:
            logging.Handler: The log handler instance.
        """
        return self._log_handler.make_handler(Board._symbols.get("logging", None))

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

    def update_manifest(self, project, starttimes=None):
        """
        Updates the dashboard with the latest data from a project object's manifest.

        Args:
            project: The SiliconCompiler project object.
            starttimes (dict, optional): A dictionary mapping (step, index) tuples
                                         to their start times. Defaults to None.
        """
        if not self._active:
            return

        self._update_render_data(project, starttimes=starttimes)

    def is_running(self) -> bool:
        """
        Checks if the dashboard rendering thread is currently active.

        Returns:
            bool: True if the dashboard is running, False otherwise.
        """
        if not self._active:
            return False

        try:
            with self._job_data_lock:
                if not self._render_thread:
                    return False

                return self._render_thread.is_alive()
        except BrokenPipeError:
            if not self._render_thread:
                return False

            return self._render_thread.is_alive()

    def end_of_run(self, project):
        """
        Signals that the run has completed, performing a final update.

        Args:
            project: The SiliconCompiler project object at the end of the run.
        """
        if not self.is_running():
            return

        self._update_render_data(project, complete=True)

    def stop(self):
        """
        Stops the dashboard rendering thread and cleans up the terminal display.
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

        # Print final render to avoid losing it
        if self.live._screen:
            self._console.print(self._get_rendable())
        self._console.show_cursor()

    def wait(self):
        """Waits for the dashboard rendering thread to finish."""
        if not self.is_running():
            return

        self._render_thread.join()

    @staticmethod
    def format_status(status: str) -> str:
        """
        Formats a node status string with rich-compatible color markup.

        Args:
            status (str): The status of the node (e.g., 'RUNNING', 'SUCCESS').

        Returns:
            str: A formatted string with the status styled for display.
        """
        return f"[node.{status.lower()}]{status.upper()}[/]"

    @staticmethod
    def format_node(design: str, jobname: str, step: str, index: int, multi_job: bool) -> str:
        """
        Formats a node's identifier for display in the dashboard.

        Args:
            design (str): The design name.
            jobname (str): The job name.
            step (str): The step name.
            index (int): The step index.
            multi_job (bool): Flag indicating if multiple jobs are running, which
                              determines the format of the identifier.

        Returns:
            str: A formatted string representing the node.
        """
        if multi_job:
            return f"{design}/{jobname}/{step}/{index}"
        else:
            return f"{step}/{index}"

    def _render_log(self, layout: Layout):
        """
        Renders the log message area of the dashboard.

        Args:
            layout (Layout): The current layout object containing dimensions.

        Returns:
            rich.group.Group or None: A renderable Group object for the log
                                      area, or None if there's no space.
        """
        if layout.log_height == 0:
            return None

        table = Table(box=None)
        table.add_column(overflow="ellipsis", no_wrap=True, vertical="bottom")
        table.show_edge = False
        table.show_lines = False
        table.show_footer = False
        table.show_header = False
        for line in self._log_handler.get_lines(layout.log_height):
            table.add_row(f"[white]{line}[/]")
        while table.row_count < layout.log_height:
            table.add_row("")

        return Group(table, Padding("", (0, 0)))

    def _render_job_dashboard(self, layout: Layout):
        """
        Renders the main job status board.

        Args:
            layout (Layout): The current layout object containing dimensions.

        Returns:
            rich.group.Group or None: A renderable Group containing the job table,
                                      or None if there is no space or no data.
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

        def get_column_header(title):
            return Board._symbols.get("table", {}).get(title, title.capitalize())

        table.add_column(get_column_header("status"))
        if layout.show_node_type:
            table.add_column(get_column_header(""))
        table.add_column(get_column_header("node"))
        table.add_column(get_column_header("time"), justify="right")
        for metric in self._metrics:
            table.add_column(get_column_header(metric), justify="right")
        if layout.job_board_show_log:
            table.add_column(get_column_header("log"))

        multi_jobs = len(job_data) > 1 or True

        # jobname, node index, priority, node order
        table_data_select = []
        for projectid, job in job_data.items():
            for n, node in enumerate(job.nodes):
                table_data_select.append(
                    (projectid, n, node["print"]["priority"], node["print"]["order"])
                )

        # sort for priority
        table_data_select = sorted(table_data_select, key=lambda d: (d[2], *d[3], d[0]))

        # trim to size
        table_data_select = table_data_select[0:layout.job_board_height]

        # sort for printing order
        table_data_select = sorted(table_data_select, key=lambda d: (d[0], *d[3], d[2]))

        table_data = []

        for projectid, node_idx, _, _ in table_data_select:
            job = job_data[projectid]
            node = job.nodes[node_idx]

            log_file = None
            if layout.job_board_show_log:
                for log in node["log"]:
                    try:
                        if os.path.getsize(log) > 0:
                            log_file = "[bright_black]{}[/]".format(log)
                            break
                    except OSError:
                        # File doesn't exist or inaccessible
                        continue

            if node["time"]["duration"] is not None:
                duration = f'{node["time"]["duration"]:.1f}s'
            elif node["time"]["start"] is not None:
                duration = f'{time.time() - node["time"]["start"]:.1f}s'
            else:
                duration = ""

            row_data = [
                Board.format_status(node["status"]),
                Board.format_node(
                    job.design, job.jobname, node["step"], node["index"],
                    multi_jobs
                ),
                duration,
                *node["metrics"],
                log_file]
            if layout.show_node_type:
                node_symbol = Board._symbols.get("node", {}).get(node["type"], "")
                row_data.insert(1, node_symbol)
            table_data.append(tuple(row_data))

        for row_data in table_data:
            table.add_row(*row_data)

        if table.row_count == 0:
            return None

        if self.__JOB_BOARD_HEADER:
            return Group(table, Padding("", (0, 0)))
        return Group(Padding("", (0, 0)), table, Padding("", (0, 0)))

    def _render_progress_bar(self, layout: Layout):
        """
        Renders the progress bar section of the dashboard.

        Args:
            layout (Layout): The current layout object containing dimensions.

        Returns:
            rich.group.Group or rich.padding.Padding: A renderable object for the
                                                      progress bars.
        """
        with self._render_data_lock:
            job_data = self._render_data.jobs.copy()

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

        job_info = []
        for name, job in job_data.items():
            done = job.finished == job.total
            job_info.append(
                (done, f"{job.design}/{job.jobname}", job.total, job.success, runtimes[name]))

        while len(job_info) > layout.progress_bar_height:
            for job in job_info:
                if job[0]:
                    # complete complete and can be removed
                    job_info.remove(job)
                    break
            # remove first job
            del job_info[0]

        if not job_info:
            return Padding("", (0, 0))

        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            MofNCompleteColumn(),
            BarColumn(bar_width=60),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn(f" {{task.fields[runtime]:>{runtime_width}.1f}}s")
        )
        for _, name, total, success, runtime in job_info:
            progress.add_task(
                f"[text.primary]Progress ({name}):",
                total=total,
                completed=success,
                runtime=runtime
            )

        return Group(progress, Padding("", (0, 0)))

    def _render(self):
        """
        Main rendering loop for the dashboard.

        This method runs in a separate thread. It waits for update events,
        fetches the latest data, re-renders the components, and updates the
        live display.
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
                    if self._render_event.wait(timeout=self._dwell):
                        self._render_event.clear()
                except:  # noqa E722
                    # Catch any multiprocessing errors
                    break

                if check_stop_event():
                    break

                update_data()
                self.live.update(self._get_rendable(), refresh=True)
                time.sleep(self._dwell)

        finally:
            update_data()
            if self.live:
                self.live.update(self._get_rendable(), refresh=True)
            else:
                self._console.print(self._get_rendable())

    def _update_layout(self) -> Layout:
        """
        Updates the layout dimensions based on the current data and console size.

        Returns:
            Layout: The updated layout object.
        """
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
        """
        Transfers job data from the shared multiprocessing dictionary to the
        local render data object, aggregating session-wide statistics.
        """
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
        Assembles the final renderable object for the `rich.live` display.

        It gets the latest layout, renders each component (job board, progress bars, log),
        and combines them into a single `rich.group.Group`.

        Returns:
            rich.group.Group: The complete, renderable dashboard layout.
        """

        layout = self._update_layout()

        new_table = self._render_job_dashboard(layout)
        new_bar = self._render_progress_bar(layout)
        footer = self._render_log(layout)

        items = []
        if new_table:
            items.extend([new_table])

        if new_bar:
            items.extend([new_bar])

        if footer:
            items.extend([footer])

        return Group(*items)

    def _update_render_data(self, project, starttimes=None, complete=False):
        """
        Extracts job and node information from a project object and updates the
        shared job data dictionary, triggering a render event.

        Args:
            project: The SiliconCompiler project object.
            starttimes (dict, optional): Dictionary of node start times. Defaults to None.
            complete (bool, optional): Flag indicating if the job is complete. Defaults to False.
        """

        if not project:
            return

        job_data = self._get_job(project, starttimes=starttimes)
        job_data.complete = complete

        if not job_data.nodes:
            return

        project_id = f"{job_data.design}/{job_data.jobname}"
        with self._job_data_lock:
            if complete and project_id in self._job_data and self._job_data[project_id].complete:
                # Dont update again, requires a start of a new run
                return
            self._job_data[project_id] = job_data
            self._board_info.data_modified = True
            self._render_event.set()

    def _get_job(self, project, starttimes=None) -> JobData:
        """
        Parses a project object to extract detailed information about the flowgraph,
        node statuses, timings, and metrics.

        This method calculates node display priority based on run status and
        dependencies.

        Args:
            project: The SiliconCompiler project object to parse.
            starttimes (dict, optional): A dictionary of node start times.
                                         Defaults to None.

        Returns:
            JobData: A data object populated with the extracted information.
        """
        if not starttimes:
            starttimes = {}

        nodes = []
        nodestatus = {}
        nodeorder = {}
        node_priority = {}
        flow_entry_nodes = set()
        flow_exit_nodes = set()
        try:
            node_inputs = {}
            node_outputs = {}
            flow = project.get("option", "flow")
            if not flow:
                raise RuntimeError("dummy error")

            runtime_flow = RuntimeFlowgraph(
                project.get("flowgraph", flow, field='schema'),
                to_steps=project.get('option', 'to'),
                prune_nodes=project.get('option', 'prune'))
            record = project.get("record", field='schema')

            execnodes = runtime_flow.get_nodes()
            lowest_priority = 3 * len(execnodes)  # 2x + 1 is lowest computed, so 3x will be lower
            for n, nodeset in enumerate(runtime_flow.get_execution_order()):
                for m, node in enumerate(nodeset):
                    if node not in execnodes:
                        continue
                    nodes.append(node)

                    node_priority[node] = lowest_priority

                    status = project.get("record", "status", step=node[0], index=node[1])
                    if status is None:
                        status = NodeStatus.PENDING
                    nodestatus[node] = status
                    nodeorder[node] = (n, m)

                    node_inputs[node] = runtime_flow.get_node_inputs(*node, record=record)
                    for in_node in project.get('flowgraph', flow, node[0], node[1], 'input'):
                        node_outputs.setdefault(in_node, set()).add(node)

            flow_entry_nodes = set(
                project.get("flowgraph", flow, field="schema").get_entry_nodes())
            flow_exit_nodes = set(runtime_flow.get_exit_nodes())

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
        except RuntimeError:
            pass

        design = project.get("option", "design")
        jobname = project.get("option", "jobname")

        job_data = JobData()
        job_data.jobname = jobname
        job_data.design = design
        totaltimes = [
            project.get("metric", "totaltime", step=step, index=index) or 0
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
                duration = project.get("metric", "tasktime", step=step, index=index)
            if (step, index) in starttimes:
                starttime = starttimes[(step, index)]

            node_metrics = []
            for metric in self._metrics:
                value = project.get('metric', metric, step=step, index=index)
                if value is None:
                    node_metrics.append("")
                else:
                    node_metrics.append(str(value))

            node_type = NodeType.OTHER
            if (step, index) in flow_entry_nodes:
                node_type = NodeType.ENTRY
            if (step, index) in flow_exit_nodes:
                node_type = NodeType.EXIT

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
                    "log": [os.path.join(
                        workdir(project, step=step, index=index, relpath=True),
                        f"{step}.log"),
                        os.path.join(
                            workdir(project, step=step, index=index, relpath=True),
                            f"sc_{step}_{index}.log")],
                    "print": {
                        "order": nodeorder[(step, index)],
                        "priority": node_priority[(step, index)]
                    },
                    "type": node_type
                }
            )

        return job_data
