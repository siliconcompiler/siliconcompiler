import atexit

from siliconcompiler.report.dashboard import AbstractDashboard
from siliconcompiler.utils.logging import SCSuppressLoggerFilter


class CliDashboard(AbstractDashboard):
    """
    A command-line interface (CLI) implementation of the AbstractDashboard.

    This class provides a concrete dashboard that renders progress and logs
    directly in the terminal. It acts as a bridge between the core `project` object
    and the `Board` class, which handles the actual `rich`-based rendering.

    It manages the lifecycle of the dashboard, including starting, stopping,
    and updating it with data from the project. While active it attaches its
    own log handler to the project's logger as an additional sink and silences
    the project's terminal handler via a filter. The terminal handler itself
    is never swapped or detached, so other components (scheduler, slurm,
    docker, etc.) keep their references to it intact.
    """

    def __init__(self, project):
        """
        Initializes the CliDashboard.

        Args:
            project: The SiliconCompiler project object this dashboard is associated with.
        """
        from siliconcompiler.utils.multiprocessing import MPManager

        super().__init__(project)

        self._dashboard = MPManager.get_dashboard()

        # Logger plumbing. When attached, _dashboard_handler is the extra
        # sink we register on the project's logger; _terminal_handler is the
        # project's terminal handler that we suppress via _suppress_filter.
        self._logger = None
        self._dashboard_handler = None
        self._terminal_handler = None
        self._suppress_filter = SCSuppressLoggerFilter()

        if self.is_running():
            # Attach logger when already running
            self.set_logger(self._project.logger)

        # Ensure the dashboard is properly stopped on program exit
        self.__exit_registered = True
        atexit.register(self.stop)

    def set_logger(self, logger):
        """
        Attaches the dashboard as an additional sink on the given logger and
        silences the project's terminal handler so the live view owns the
        screen. Passing ``None`` detaches the dashboard sink and restores
        normal terminal output.

        The project's ``_logger_console`` handler is left in place — only its
        emit is suppressed via a filter — so any external code that holds a
        reference to it (taskscheduler, schedulernode, etc.) keeps working.

        Args:
            logger (logging.Logger): The logger to attach to, or ``None`` to
                detach.
        """
        if logger is None:
            self._detach_logger()
            self._logger = None
            return

        if self._dashboard_handler is not None:
            # Already attached. Re-attaching to a different logger is not a
            # supported flow (the project's logger doesn't change), so this
            # also covers the "called twice with same logger" case.
            self._logger = logger
            return

        if not self._dashboard._active:
            # Headless / non-terminal environment — nothing to attach to.
            self._logger = logger
            return

        self._logger = logger
        self._terminal_handler = self._project._logger_console

        # The dashboard buffer follows the terminal handler's current
        # formatter, so any in-run formatter swap (e.g. SCBlankLoggerFormatter
        # during a TaskScheduler run, or the step/index formatter inside a
        # SchedulerNode) is reflected in the dashboard log pane without
        # explicit synchronization.
        self._dashboard_handler = self._dashboard.make_log_hander(
            formatter_source=self._terminal_handler)
        self._logger.addHandler(self._dashboard_handler)

        # Silence the terminal handler so log emits don't corrupt the live
        # display while the dashboard owns the screen.
        self._terminal_handler.addFilter(self._suppress_filter)
        self._suppress_filter.active = True

    def open_dashboard(self):
        """
        Starts the dashboard rendering thread.

        This method ensures the logger is set and then tells the underlying
        `Board` object to start its live-rendering thread.
        """

        if not self.__exit_registered:
            # Ensure the dashboard is properly stopped on program exit
            self.__exit_registered = True
            atexit.register(self.stop)

        self.set_logger(self._project.logger)

        self._dashboard.open_dashboard()

    def update_manifest(self, payload=None):
        """
        Updates the dashboard with the latest data from the project's manifest.

        This method is called to refresh the dashboard's display with the
        current state of the compilation flow.

        Args:
            payload (dict, optional): A dictionary that can contain additional
                                      data, such as node start times. Defaults to None.
        """
        starttimes = None
        if payload and "starttimes" in payload:
            starttimes = payload["starttimes"]
        self._dashboard.update_manifest(self._project, starttimes=starttimes)

    def update_graph_manifests(self):
        """Placeholder method for updating graph manifests. Currently not implemented."""
        pass

    def is_running(self):
        """
        Checks if the dashboard rendering thread is currently active.

        Returns:
            bool: True if the dashboard is running, False otherwise.
        """
        return self._dashboard.is_running()

    def end_of_run(self):
        """
        Signals to the dashboard that the compilation run has finished.

        This triggers a final update of the dashboard to show the completed state.
        """
        self._dashboard.end_of_run(self._project)

    def stop(self):
        """
        Stops the dashboard and restores normal terminal logging.
        """
        self._dashboard.end_of_run(self._project)

        self._dashboard.stop()

        self._detach_logger()

        if self.__exit_registered:
            atexit.unregister(self.stop)
            self.__exit_registered = False

    def _detach_logger(self):
        """
        Remove the dashboard's log sink and unsuppress the terminal handler.
        Safe to call when nothing is attached. Idempotent.
        """
        if self._terminal_handler is not None:
            try:
                self._terminal_handler.removeFilter(self._suppress_filter)
            except Exception:
                pass
            self._suppress_filter.active = False

        if self._dashboard_handler is not None and self._logger is not None:
            try:
                self._logger.removeHandler(self._dashboard_handler)
            except Exception:
                pass

        self._dashboard_handler = None
        self._terminal_handler = None

    def wait(self):
        """
        Waits for the dashboard rendering thread to complete.

        This is a blocking call that is useful for ensuring the dashboard has
        fully shut down before the main program exits.
        """
        self._dashboard.wait()
