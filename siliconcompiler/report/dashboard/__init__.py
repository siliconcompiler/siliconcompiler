import weakref

from abc import ABC, abstractmethod
from enum import Enum


def _dead_ref():
    """Stand-in for a resolved-empty weak reference (used after unpickling)."""
    return None


class WeakAtexitCall:
    """
    A picklable, zero-argument trampoline that invokes a bound method through
    a :class:`weakref.WeakMethod`, suitable for :func:`atexit.register`.

    Registering a bound method directly with ``atexit`` (e.g.
    ``atexit.register(self.stop)``) stores a strong reference to the instance
    in the atexit registry, keeping it — and everything it transitively
    references — alive until interpreter exit. For a dashboard that means the
    whole :class:`~siliconcompiler.Project` leaks and can never be garbage
    collected.

    This trampoline holds only a weak reference to the bound method. When
    invoked at exit it resolves the weak reference and calls the method only
    if the instance is still alive; otherwise it is a harmless no-op, letting
    the garbage collector reclaim the instance early.

    A :class:`weakref.WeakMethod` cannot be pickled, and the reference would be
    meaningless in another process, so the trampoline pickles as a dead no-op.
    This matters because it is stored on the dashboard instance, and a
    dashboard may itself be pickled to a subprocess (e.g. the
    :class:`~siliconcompiler.report.dashboard.web.WebDashboard` sent to the
    Streamlit process). The subprocess never re-registers atexit hooks, so the
    dead stand-in is correct there.
    """

    def __init__(self, method):
        try:
            self._ref = weakref.WeakMethod(method)
        except TypeError:
            # ``method`` is not a bound method (e.g. a plain function, or a
            # unittest.mock double swapped in for one). Such a callable pins no
            # instance, so there is nothing to weaken — resolve to it directly
            # behind the same zero-arg protocol WeakMethod provides.
            self._ref = lambda: method

    def __call__(self):
        target = self._ref()
        if target is not None:
            target()

    def __getstate__(self):
        # A WeakMethod is not picklable and carries no meaning across a
        # process boundary; drop it so an embedding object can still be
        # pickled to a subprocess.
        return {}

    def __setstate__(self, state):
        self._ref = _dead_ref


def weak_atexit_call(method):
    """
    Build a :class:`WeakAtexitCall` trampoline for ``method``.

    Args:
        method: A bound method to invoke at interpreter exit.

    Returns:
        WeakAtexitCall: A picklable, zero-argument callable to pass to
        ``atexit.register`` (and later ``atexit.unregister``).
    """
    return WeakAtexitCall(method)


class DashboardType(Enum):
    """
    An enumeration to represent the available types of dashboards.

    This allows for a standardized way to specify whether to launch a
    web-based dashboard or a command-line interface (CLI) dashboard.

    Attributes:
        WEB: Represents a web-based dashboard.
        CLI: Represents a command-line interface dashboard.
    """
    WEB = 'web'
    CLI = 'cli'


class AbstractDashboard(ABC):
    """
    Abstract base class defining the interface for dashboard implementations.

    This class establishes a contract for all concrete dashboard classes,
    such as `CliDashboard` or a future `WebDashboard`. It ensures that any
    dashboard implementation will have a consistent set of methods for
    starting, stopping, and updating its state, regardless of its specific
    rendering technology (e.g., terminal UI or web browser).
    """

    @abstractmethod
    def __init__(self, project):
        """
        Initializes the dashboard with a reference to the project object.

        Args:
            project: The SiliconCompiler project object whose data will be displayed
                  by the dashboard.
        """
        self._project = project

    @abstractmethod
    def open_dashboard(self):
        """
        Opens and starts the dashboard service.

        This method should handle all setup required to make the dashboard
        visible and active, such as starting a rendering thread or a web server.
        """
        pass

    @abstractmethod
    def update_manifest(self, payload=None):
        """
        Updates the dashboard with the latest information from the project's manifest.

        This method is the primary mechanism for pushing new data to the
        dashboard as the compilation flow progresses.

        Args:
            payload (dict, optional): A dictionary of metadata to pass to the
                dashboard. A common use is to provide node start times, e.g.,
                `{"starttimes": {<node_tuple>: time, ...}}`. Defaults to None.
        """
        pass

    @abstractmethod
    def update_graph_manifests(self):
        """
        Updates the manifest files for all associated graph projects.

        This is intended for scenarios where a dashboard might need to display
        data from multiple, related project objects (e.g., in a multi-job run).
        """
        pass

    @abstractmethod
    def is_running(self):
        """
        Checks if the dashboard service is currently active.

        Returns:
            bool: True if the dashboard is running, False otherwise.
        """
        pass

    @abstractmethod
    def end_of_run(self):
        """
        Notifies the dashboard that a compilation run has completed.

        This allows the dashboard to perform any final updates or cleanup
        actions, such as displaying a final summary.
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Stops the dashboard service if it's running.

        This method should gracefully shut down any background processes,
        threads, or servers associated with the dashboard.
        """
        pass

    @abstractmethod
    def wait(self):
        """
        Waits for the dashboard service to terminate.

        This is a blocking call that should not return until the dashboard
        has fully shut down. It is useful for ensuring a clean exit.
        """
        pass
