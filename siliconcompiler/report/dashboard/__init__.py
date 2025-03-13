from abc import ABC, abstractmethod


class AbstractDashboard(ABC):
    """
    Abstract base class defining the interface for dashboard implementations.
    Any concrete dashboard implementation should inherit from this class and
    implement all abstract methods.
    """

    @abstractmethod
    def __init__(self, chip, port=None, graph_chips=None):
        """
        Initialize the dashboard.
        
        Args:
            chip: The chip object to display in the dashboard
            port (int, optional): Port number to serve the dashboard on
            graph_chips (list, optional): List of additional chip objects to display
        """
        pass

    @abstractmethod
    def open_dashboard(self):
        """
        Open and start the dashboard service.
        """
        pass

    @abstractmethod
    def update_manifest(self):
        """
        Update the manifest file with the latest chip information.
        """
        pass

    @abstractmethod
    def update_graph_manifests(self):
        """
        Update the manifest files for all graph chips.
        """
        pass

    @abstractmethod
    def is_running(self):
        """
        Check if the dashboard is currently running.
        
        Returns:
            bool: True if the dashboard is running, False otherwise
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Stop the dashboard service if it's running.
        """
        pass

    @abstractmethod
    def wait(self):
        """
        Wait for the dashboard service to terminate.
        """
        pass
    
    @staticmethod
    @abstractmethod
    def get_next_port():
        """
        Get the next available port for the dashboard.
        
        Returns:
            int: An available port number or None if no port is available
        """
        pass