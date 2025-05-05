import os
import time
import tempfile
import json

import multiprocessing
import subprocess
import atexit
import shutil
import fasteners
import signal
import socketserver

from siliconcompiler.report.dashboard import AbstractDashboard
from siliconcompiler.report.dashboard.web import utils


class WebDashboard(AbstractDashboard):
    __port = 8501

    @staticmethod
    def __signal_handler(signal, frame):
        # used to avoid issues during shutdown
        pass

    def __init__(self, chip, port=None, graph_chips=None):
        try:
            from streamlit.web import bootstrap  # noqa: F401
        except ModuleNotFoundError:
            raise NotImplementedError('streamlit is not available')

        super().__init__(chip)

        if not port:
            port = WebDashboard.get_next_port()
        if not port:
            port = WebDashboard.__port

        self.__dashboard = None
        self.__chip = chip
        self.__directory = tempfile.mkdtemp(prefix='sc_dashboard_',
                                            suffix=f'_{self.__chip.design}')
        self.__manifest = os.path.join(self.__directory, 'manifest.json')
        self.__manifest_lock = os.path.join(self.__directory, 'manifest.lock')
        self.__port = port
        dirname = os.path.dirname(__file__)
        self.__streamlit_file = os.path.join(dirname, 'viewer.py')

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

        # pass in a json object called __graph_chips
        # the key is the chip_name and value is the filepath
        # if another argument is passed

        # use of list is to preserve order
        self.__graph_chips = []
        graph_chips_config = []
        if graph_chips:
            for chip_object_and_name in graph_chips:
                chip_file_path = \
                    os.path.join(self.__directory,
                                 f"{chip_object_and_name['name']}.json")
                self.__graph_chips.append({
                    'chip': chip_object_and_name['chip'],
                    'name': chip_file_path
                })
                graph_chips_config.append({
                    "path": chip_file_path,
                    "cwd": utils.get_chip_cwd(
                        chip_object_and_name['chip'],
                        chip_object_and_name['cfg_path'])
                })

        self.__config = {
            "manifest": self.__manifest,
            "lock": self.__manifest_lock,
            "graph_chips": graph_chips_config
        }

        self.__sleep_time = 0.5
        self.__signal_handler = None

        self.__lock = fasteners.InterProcessLock(self.__manifest_lock)

        atexit.register(self.__cleanup)

    def open_dashboard(self):
        with open(self.__get_config_file(), 'w') as f:
            json.dump(self.__config, f, indent=4)

        self.update_manifest()

        self.update_graph_manifests()

        self.__dashboard = multiprocessing.Process(
            target=self._run_streamlit_bootstrap)

        self.__signal_handler = signal.signal(signal.SIGINT, WebDashboard.__signal_handler)

        self.__dashboard.start()

    def update_manifest(self, payload=None):
        if not self.__manifest:
            return

        new_file = f"{self.__manifest}.new.json"
        self.__chip.write_manifest(new_file)

        with self.__lock:
            shutil.move(new_file, self.__manifest)

    def update_graph_manifests(self):
        for chip_object_and_name in self.__graph_chips:
            chip = chip_object_and_name['chip']
            file_path = chip_object_and_name['name']
            chip.write_manifest(file_path)

    def __get_config_file(self):
        return os.path.join(self.__directory, 'config.json')

    def is_running(self):
        if self.__dashboard is None:
            return False

        if self.__dashboard.is_alive():
            return True

        self.__dashboard = None
        self.__manifest = None
        return False

    def end_of_run(self):
        pass

    def stop(self):
        if not self.is_running():
            return

        while self.__dashboard.is_alive():
            self.__dashboard.terminate()
            self._sleep()

        if self.__signal_handler:
            signal.signal(signal.SIGINT, self.__signal_handler)

        self.__dashboard = None
        self.__manifest = None
        self.__signal_handler = None

    def wait(self):
        self.__dashboard.join()

    def _sleep(self):
        time.sleep(self.__sleep_time)

    def _run_streamlit_bootstrap(self):
        from streamlit.web import bootstrap
        from streamlit import config as _config

        for config, val in self.__streamlit_args:
            _config.set_option(config, val)

        bootstrap.run(self.__streamlit_file,
                      False,
                      [self.__get_config_file()],
                      flag_options={})

    def __run_streamlit_subproc(self):
        cmd = ['streamlit', 'run',
               self.__streamlit_file, self.__get_config_file()]
        for config, val in self.__streamlit_args:
            cmd.append(f'--{config}')
            cmd.append(val)

        subprocess.Popen(cmd)

    def __cleanup(self):
        self.stop()

        if os.path.exists(self.__directory):
            shutil.rmtree(self.__directory)

    @staticmethod
    def get_next_port():
        with socketserver.TCPServer(("localhost", 0), None) as s:
            return s.server_address[1]
        return None
