import threading
import shutil
import fasteners
import time

from rich.theme import Theme
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.console import Console
from rich.console import Group
from rich.padding import Padding

from siliconcompiler.report.dashboard import AbstractDashboard
from siliconcompiler.flowgraph import nodes_to_execute


class CliDashboard(AbstractDashboard):
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
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "ignore": "bright_black",
            # Custom style for headers
            "header": "bold underline cyan",
        }
    )

    def __init__(self, chip):
        super().__init__(chip)

        self._lock = fasteners.InterProcessLock(self._manifest_lock)
        self.__render_event = threading.Event()
        self.__render_stop_event = threading.Event()
        self.__render_thread = threading.Thread(target=self.__render, daemon=True)

        self.__starttime = time.time()

        self._render_data = {}
        self._render_data_lock = threading.Lock()

        self.console = Console(theme=CliDashboard.__theme)

    def open_dashboard(self):
        """Starts the dashboard rendering thread if it is not already running."""
        if not self.__render_thread.is_alive():
            self.__update_render_data()
            self.__render_thread.start()

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

        self.__update_render_data()
        self.__render_event.set()

    def update_graph_manifests(self):
        """Placeholder method for updating graph manifests. Currently not implemented."""
        pass

    def is_running(self):
        """Returns True to indicate that the dashboard is running."""
        return True

    def stop(self):
        """
        Stops the dashboard rendering thread and ensures all rendering operations are completed.
        """
        self.__render_stop_event.set()
        self.__render_event.set()
        # Wait for rendering to finish
        self.__render_thread.join()

    def wait(self):
        """Waits for the dashboard rendering thread to finish."""
        self.__render_thread.join()

    def __format_status(self, status: str):
        """
        Formats the status of a node for display in the dashboard.

        Args:
            status (str): The status of the node (e.g., 'running', 'success', 'error').

        Returns:
            str: A formatted string with the status styled for display.
        """
        status_map = {
            "running": "[warning]RUNNING[/]",
            "success": "[success]SUCCESS[/]",
            "error": "[error]ERROR[/]",
        }
        return status_map.get(status, f"[ignore]{status.upper()}[/]")

    def __format_node(self, design, jobname, step, index) -> str:
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
        return f"[accent]{design}/[/][text.primary]{jobname}/{step}/{index}[/]"

    def __render_job_dashboard(self):
        """
        Creates a table of jobs and their statuses for display in the dashboard.

        Returns:
            Group: A Rich Group object containing tables for each job.
        """
        with self._render_data_lock:
            job_data = self._render_data.copy()

        job_dashboards = []
        for jobname, job in job_data.items():
            table = Table(box=None)
            table.show_edge = False
            table.show_lines = False
            table.show_footer = False
            table.show_header = False
            table.add_column()
            table.add_column()
            table.add_column()

            for node in job["nodes"]:
                table.add_row(
                    self.__format_node(
                        node["design"], node["jobname"], node["step"], node["index"]
                    ),
                    self.__format_status(node["status"]),
                    "Log: {}".format(node["log"])
                    if node["status"] in ["running", "timeout", "error"]
                    else "",
                )

            job_dashboards.append(table)

        return Group(*job_dashboards)

    def __render_progress_bar(self):
        """
        Creates progress bars showing job completion for display in the dashboard.

        Returns:
            Group: A Rich Group object containing progress bars for each job.
        """
        with self._render_data_lock:
            job_data = self._render_data.copy()

        progress_bars = []
        for jobname in job_data.keys():
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            )

            progress.add_task(
                f"[text.primary]Progress ({jobname}):",
                total=job_data[jobname]["total"],
                completed=job_data[jobname]["success"],
            )

            progress_bars.append(progress)

        return Group(*progress_bars)

    def __render_final(self):
        """
        Creates a summary of the final results, including runtime, passed, and failed jobs.

        Returns:
            Padding: A Rich Padding object containing the summary text.
        """
        success = 0
        error = 0
        total = 0
        finished = 0
        for jobname, job in self._render_data.items():
            total += job["total"]
            finished += job["finished"]
            success += job["success"]
            error += job["error"]

        runtime = time.time() - self.__starttime
        if finished != 0 and finished == total:
            return Padding(
                f"[text.primary]Results ({runtime:.2f})s\n"
                f"     [success]{success} passed[/]\n"
                f"     [error]{error} failed[/]\n"
            )

        return Padding("", (0, 0))

    def __render(self):
        """
        Main rendering method for the TUI. Continuously updates the dashboard
        with the latest data until the stop event is set.
        """
        with Live(self.__get_rendable(), console=self.console, screen=False) as live:
            while not self.__render_stop_event.is_set():
                self.__render_event.wait()
                self.__render_event.clear()

                if self.__render_stop_event.is_set():
                    break

                live.update(self.__get_rendable(), refresh=True)

    def __get_rendable(self):
        """
        Combines all dashboard components (job table, progress bars, final summary)
        into a single renderable group.

        Returns:
            Group: A Rich Group object containing all dashboard components.
        """
        new_table = self.__render_job_dashboard()
        new_bar = self.__render_progress_bar()
        finished = self.__render_final()

        panel_group = Group(
            Padding("", (0, 0)),
            new_table,
            Padding("", (0, 0)),
            new_bar,
            Padding("", (0, 0)),
            finished,
        )

        return panel_group

    def __update_render_data(self):
        """
        Updates the render data with the latest job and node information from the chip object.
        This data is used to populate the dashboard.
        """
        steps = nodes_to_execute(self._chip)

        design = self._chip.get("design")
        job_name = self._chip.get("option", "jobname")

        job_dict = {
            "total": 0,
            "success": 0,
            "error": 0,
            "finished": 0,
            "runtime": 0,
            "nodes": [],
        }

        for step in steps:
            status = self._chip.get("record", "status", step=step[0], index=step[1])
            if not status:
                status = "none"
            job_dict["nodes"].append(
                {
                    "design": design,
                    "jobname": job_name,
                    "step": step[0],
                    "index": step[1],
                    "status": status,
                    "log": "path/to/file.log",
                }
            )

            if status == "skipped":
                continue

            job_dict["total"] += 1
            if status in ["error", "timeout"]:
                job_dict["error"] += 1
            if status == "success":
                job_dict["success"] += 1
            if status in ["error", "timeout", "success"]:
                job_dict["finished"] += 1

        with self._render_data_lock:
            self._render_data[job_name] = job_dict
