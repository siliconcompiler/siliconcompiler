from abc import ABC, abstractmethod
from enum import Enum


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
