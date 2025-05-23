from siliconcompiler.report.dashboard import AbstractDashboard
from siliconcompiler.report.dashboard.cli.board import Board


class CliDashboard(AbstractDashboard):

    def __init__(self, chip):
        super().__init__(chip)

        self._dashboard = Board()

        self.__logger_console = None

        self._logger = chip.logger

    def set_logger(self, logger):
        """
        Sets the logger for the dashboard.

        Args:
            logger (logging.Logger): The logger to set.
        """
        self._logger = logger
        if self._logger and self._dashboard._active:
            # Hijack the console
            self._logger.removeHandler(self._chip.logger._console)
            self.__logger_console = self._chip.logger._console
            self._chip.logger._console = self._dashboard._log_handler
            self._logger.addHandler(self._dashboard._log_handler)
            self._chip._init_logger_formats()

    def open_dashboard(self):
        """Starts the dashboard rendering thread if it is not already running."""

        self.set_logger(self._logger)

        self._dashboard.open_dashboard()

    def update_manifest(self, payload=None):
        """
        Updates the manifest file with the latest data from the chip object.
        This ensures that the dashboard reflects the current state of the chip.
        """
        starttimes = None
        if payload and "starttimes" in payload:
            starttimes = payload["starttimes"]
        self._dashboard.update_manifest(self._chip, starttimes=starttimes)

    def update_graph_manifests(self):
        """Placeholder method for updating graph manifests. Currently not implemented."""
        pass

    def is_running(self):
        """Returns True to indicate that the dashboard is running."""
        return self._dashboard.is_running()

    def end_of_run(self):
        """
        Stops the dashboard rendering thread and ensures all rendering operations are completed.
        """
        self._dashboard.end_of_run(self._chip)

    def stop(self):
        """
        Stops the dashboard rendering thread and ensures all rendering operations are completed.
        """
        self._dashboard.end_of_run(self._chip)

        self._dashboard.stop()

        # Restore logger
        if self.__logger_console:
            self._logger.removeHandler(self._dashboard._log_handler)
            self._chip.logger._console = self.__logger_console
            self._logger.addHandler(self.__logger_console)
            self._chip._init_logger_formats()
            self.__logger_console = None

    def wait(self):
        """Waits for the dashboard rendering thread to finish."""
        self._dashboard.wait()
