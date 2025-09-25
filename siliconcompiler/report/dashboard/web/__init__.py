import json
import os
import time
import tempfile

import atexit
import fasteners
import multiprocessing
import shutil
import signal
import socketserver
import subprocess

from siliconcompiler.report.dashboard import AbstractDashboard
from siliconcompiler.report.dashboard.web import utils


class WebDashboard(AbstractDashboard):
    """
    A web-based dashboard for SiliconCompiler that uses the Streamlit framework.

    This class launches a Streamlit server in a separate process to provide a
    real-time, interactive web UI for monitoring a project's compilation flow.
    It manages a temporary directory for passing manifests and configuration
    between the main SC process and the Streamlit dashboard process.

    Args:
        project (Project): The main project object to display.
        port (int, optional): The port to run the Streamlit server on. If not
            provided, it will search for an available port.
        graph_projs (list, optional): A list of other project objects to include
            for comparison or display in the dashboard.
    """
    __port = 8501

    @staticmethod
    def __signal_handler(signal, frame):
        """A no-op signal handler to gracefully manage shutdown."""
        # used to avoid issues during shutdown
        pass

    def __init__(self, project, port=None, graph_projs=None):
        """
        Initializes the WebDashboard.
        """
        try:
            from streamlit.web import bootstrap  # noqa: F401
        except ModuleNotFoundError:
            raise NotImplementedError('streamlit is not available for dashboard')

        super().__init__(project)

        if not port:
            port = WebDashboard.get_next_port()
        if not port:
            port = WebDashboard.__port

        self.__dashboard = None
        self.__project = project
        self.__directory = tempfile.mkdtemp(prefix='sc_dashboard_',
                                            suffix=f'_{self.__project.name}')
        self.__manifest = os.path.join(self.__directory, 'manifest.json')
        self.__manifest_lock = os.path.join(self.__directory, 'manifest.lock')
        self.__port = port
        dirname = os.path.dirname(__file__)
        self.__streamlit_file = os.path.join(dirname, 'viewer.py')

        # Configure Streamlit server options
        self.__streamlit_args = [
            ("browser.gatherUsageStats", False),
            ("browser.serverPort", self.__port),
            ("logger.level", 'error'),
            ("runner.fastReruns", True),
            ("server.port", self.__port),
            ("client.toolbarMode", "viewer")
        ]
        if "PYTEST_CURRENT_TEST" in os.environ:
            self.__streamlit_args.append(("server.headless", True))

        # Prepare configuration for any additional projects to be displayed
        self.__graph_projects = []
        graph_projects_config = []
        if graph_projs:
            for project_object_and_name in graph_projs:
                project_file_path = \
                    os.path.join(self.__directory,
                                 f"{project_object_and_name['name']}.json")
                self.__graph_projects.append({
                    'project': project_object_and_name['project'],
                    'name': project_file_path
                })
                graph_projects_config.append({
                    "path": project_file_path,
                    "cwd": utils.get_project_cwd(
                        project_object_and_name['project'],
                        project_object_and_name['cfg_path'])
                })

        # Final configuration object to be passed to the Streamlit process
        self.__config = {
            "manifest": self.__manifest,
            "lock": self.__manifest_lock,
            "graph_projects": graph_projects_config
        }

        self.__sleep_time = 0.5
        self.__signal_handler = None

        self.__lock = fasteners.InterProcessLock(self.__manifest_lock)

        # Ensure cleanup is called on exit
        atexit.register(self.__cleanup)

    def open_dashboard(self):
        """
        Starts the Streamlit dashboard server in a new process.

        This method writes the necessary configuration and manifests, then
        launches the Streamlit bootstrap function in a separate process.
        """
        # Write the configuration file for the Streamlit app to read
        with open(self.__get_config_file(), 'w') as f:
            json.dump(self.__config, f, indent=4)

        self.update_manifest()
        self.update_graph_manifests()

        # Launch Streamlit in a separate process
        self.__dashboard = multiprocessing.Process(
            target=self._run_streamlit_bootstrap)

        # Temporarily override the SIGINT handler for graceful shutdown
        self.__signal_handler = signal.signal(signal.SIGINT, WebDashboard.__signal_handler)

        self.__dashboard.start()

    def update_manifest(self, payload=None):
        """
        Writes the main project's manifest to the shared temporary directory.

        This method is the primary way data is passed from the main process
        to the dashboard process. It uses a file lock to prevent race conditions.
        """
        if not self.__manifest:
            return

        # Write to a new file and then move it to be atomic
        new_file = f"{self.__manifest}.new.json"
        self.__project.write_manifest(new_file)

        with self.__lock:
            shutil.move(new_file, self.__manifest)

    def update_graph_manifests(self):
        """
        Writes the manifests for all additional graph projects to the shared directory.
        """
        for project_object_and_name in self.__graph_projects:
            project = project_object_and_name['project']
            file_path = project_object_and_name['name']
            project.write_manifest(file_path)

    def __get_config_file(self):
        """Returns the path to the dashboard's JSON configuration file."""
        return os.path.join(self.__directory, 'config.json')

    def is_running(self):
        """
        Checks if the dashboard server process is currently running.

        Returns:
            bool: True if the dashboard is running, False otherwise.
        """
        if self.__dashboard is None:
            return False

        if self.__dashboard.is_alive():
            return True

        # Process is no longer alive, so clean up
        self.__dashboard = None
        self.__manifest = None
        return False

    def end_of_run(self):
        """A placeholder method to fulfill the AbstractDashboard interface."""
        pass

    def stop(self):
        """
        Stops the dashboard server process.
        """
        if not self.is_running():
            return

        # Terminate the process
        while self.__dashboard.is_alive():
            self.__dashboard.terminate()
            self._sleep()

        # Restore the original signal handler
        if self.__signal_handler:
            signal.signal(signal.SIGINT, self.__signal_handler)

        # Clean up state
        self.__dashboard = None
        self.__manifest = None
        self.__signal_handler = None

    def wait(self):
        """
        Waits for the dashboard server process to terminate.
        """
        if self.is_running():
            self.__dashboard.join()

    def _sleep(self):
        """Pauses execution for a short duration."""
        time.sleep(self.__sleep_time)

    def _run_streamlit_bootstrap(self):
        """
        The target function for the multiprocessing.Process.

        This function configures and runs the Streamlit application.
        """
        from streamlit.web import bootstrap
        from streamlit import config as _config

        # Set all configured Streamlit options
        for config, val in self.__streamlit_args:
            _config.set_option(config, val)

        # Run the Streamlit script
        bootstrap.run(self.__streamlit_file,
                      False,
                      [self.__get_config_file()],
                      flag_options={})

    def __run_streamlit_subproc(self):
        """
        An alternative (unused) method to run Streamlit using a subprocess.
        """
        cmd = ['streamlit', 'run',
               self.__streamlit_file, self.__get_config_file()]
        for config, val in self.__streamlit_args:
            cmd.append(f'--{config}')
            cmd.append(str(val))

        subprocess.Popen(cmd)

    def __cleanup(self):
        """
        Cleans up resources by stopping the dashboard and removing the temp directory.
        This method is registered with atexit to be called on program exit.
        """
        self.stop()

        if os.path.exists(self.__directory):
            shutil.rmtree(self.__directory)

    @staticmethod
    def get_next_port():
        """
        Finds an available TCP port on the local machine.

        Returns:
            int or None: An available port number, or None if one cannot be found.
        """
        try:
            with socketserver.TCPServer(("localhost", 0), None) as s:
                return s.server_address[1]
        except OSError:
            return None
