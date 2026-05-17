import atexit

from siliconcompiler.report.dashboard import AbstractDashboard
from siliconcompiler.utils.logging import SCSuppressLoggerFilter


class CliDashboard(AbstractDashboard):
    """
    A command-line interface (CLI) implementation of the AbstractDashboard.

    Acts as a thin per-project facade over the singleton :class:`Board`,
    which actually owns the rich Live render thread. Any number of
    ``CliDashboard`` instances can exist at once — every Project gets one,
    and transient Projects (created via ``__setstate__`` / ``copy()`` /
    ``Project.from_manifest``) get their own — but only the one whose
    :meth:`open_dashboard` is called by an active run claims the Board's
    quit-handler slot. Transient instances stay dormant: they don't attach
    log handlers, install filters, or register quit callbacks.

    While active, this dashboard attaches its own log handler to the
    project's logger as an additional sink and silences the project's
    terminal handler via :class:`SCSuppressLoggerFilter`. The terminal
    handler itself is never swapped or detached, so other components
    (scheduler, slurm, docker, etc.) keep their references to it intact.
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

        # Stable references to our bound subscribers. Bound-method
        # objects are created fresh on each attribute access (so
        # ``a.f is a.f`` is False), which would make register/unregister
        # against the Board's subscriber sets unreliable. Capturing once
        # gives us a single identity for both subscribe and unsubscribe.
        self._quit_callback = self._handle_user_quit
        self._resume_callback = self._handle_user_resume

        # Deliberately NOT subscribing to the Board's quit handler here,
        # and NOT auto-attaching the logger. We are only an *interface*
        # to the singleton Board — transient Project instances (from
        # __setstate__, deepcopy, Project.from_manifest, etc.) construct
        # their own CliDashboard but never call open_dashboard. They have
        # no logger plumbing to tear down, so they have no business
        # subscribing. The active owner subscribes in open_dashboard.

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
            if logger is self._logger:
                return
            # Different logger: move the dashboard handler over so we don't
            # leak it on the old logger. In practice the project's logger
            # is invariant, but the move is cheap and avoids a latent bug
            # if that ever changes.
            try:
                self._logger.removeHandler(self._dashboard_handler)
            except Exception:
                pass
            logger.addHandler(self._dashboard_handler)
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

        # Subscribe to the Board's quit / resume notifications now that
        # we own logger plumbing worth tearing down (and re-engaging).
        # Both are idempotent on the Board side, so repeated
        # open_dashboard calls are safe. The resume subscription
        # deliberately survives qq teardown — that's what lets ``d d``
        # find a subscriber later.
        self._dashboard.register_quit_handler(self._quit_callback)
        self._dashboard.register_resume_handler(self._resume_callback)

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

        # Unsubscribe from the Board's quit + resume notifications.
        # Other CliDashboard instances' subscriptions are untouched.
        self._dashboard.unregister_quit_handler(self._quit_callback)
        self._dashboard.unregister_resume_handler(self._resume_callback)

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

    def _handle_user_quit(self):
        """
        Invoked from the dashboard render thread's finally block (after the
        live view is already torn down) when the user double-presses 'q'.
        Detaches our log sink so terminal output flows again, and removes
        our quit subscription from the Board. The resume subscription is
        intentionally left in place — that's how the resume watcher
        finds us when the user later presses 'd' twice.

        MUST NOT call ``self.stop()`` or anything that joins the render
        thread: we are running on that thread.
        """
        try:
            self._detach_logger()
        except Exception:
            pass

        try:
            self._dashboard.unregister_quit_handler(self._quit_callback)
        except Exception:
            pass

        # atexit unregistration deliberately omitted here: the resume
        # path may bring us back, and a re-engaged dashboard still wants
        # its atexit-driven cleanup to run on program exit.

    def _handle_user_resume(self):
        """
        Invoked from the Board's resume watcher thread when the user
        confirms a re-enable via ``d d``. Re-runs the open-dashboard
        path so our logger plumbing is reattached and a fresh render
        thread starts.

        Safe to call from the watcher thread: ``Board.open_dashboard``
        tears down the watcher itself, with a self-call guard that
        avoids the watcher trying to join its own thread.
        """
        try:
            self.open_dashboard()
        except Exception:
            pass

    def wait(self):
        """
        Waits for the dashboard rendering thread to complete.

        This is a blocking call that is useful for ensuring the dashboard has
        fully shut down before the main program exits.
        """
        self._dashboard.wait()
