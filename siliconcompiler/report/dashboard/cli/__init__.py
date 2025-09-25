import atexit

from siliconcompiler.report.dashboard import AbstractDashboard


class CliDashboard(AbstractDashboard):
    """
    A command-line interface (CLI) implementation of the AbstractDashboard.

    This class provides a concrete dashboard that renders progress and logs
    directly in the terminal. It acts as a bridge between the core `project` object
    and the `Board` class, which handles the actual `rich`-based rendering.

    It manages the lifecycle of the dashboard, including starting, stopping,
    and updating it with data from the project. A key feature is its ability to
    "hijack" the standard logger to redirect log messages to its own display area.

    Attributes:
        _dashboard: An instance of the underlying `Board` class that manages
                    the `rich` live display.
        _logger: The `logging.Logger` instance associated with the dashboard.
        __logger_console: A private attribute to store the original console
                          handler of the logger before it's replaced.
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

        self.__logger_console = None

        self._logger = None

        if self.is_running():
            # Attach logger when already running
            self.set_logger(self._project.logger)

        # Ensure the dashboard is properly stopped on program exit
        self.__exit_registered = True
        atexit.register(self.stop)

    def set_logger(self, logger):
        """
        Sets the logger for the dashboard and hijacks its console handler.

        This method replaces the project's default console log handler with one
        that directs log messages to the dashboard's internal log buffer.
        The original handler is saved so it can be restored later.

        Args:
            logger (logging.Logger): The logger instance to attach to.
        """
        if self._logger == logger:
            return

        self._logger = logger
        if self._logger and self._dashboard._active:
            # Hijack the console handler to redirect logs to the dashboard
            self._logger.removeHandler(self._project._logger_console)
            self.__logger_console = self._project._logger_console
            self._project._logger_console = self._dashboard.make_log_hander()
            self._logger.addHandler(self._project._logger_console)
            self._project._logger_console.setFormatter(self.__logger_console.formatter)

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
        Stops the dashboard and restores the original logger configuration.

        This method performs a final update, stops the rendering thread, and
        restores the original console handler to the logger.
        """
        self._dashboard.end_of_run(self._project)

        self._dashboard.stop()

        # Restore the original logger handler
        if self.__logger_console and self._logger:
            self._logger.removeHandler(self._project._logger_console)
            formatter = self._project._logger_console.formatter
            self._project._logger_console = self.__logger_console
            self._logger.addHandler(self.__logger_console)
            self.__logger_console.setFormatter(formatter)
            self.__logger_console = None

        if self.__exit_registered:
            atexit.unregister(self.stop)
            self.__exit_registered = False

    def wait(self):
        """
        Waits for the dashboard rendering thread to complete.

        This is a blocking call that is useful for ensuring the dashboard has
        fully shut down before the main program exits.
        """
        self._dashboard.wait()
