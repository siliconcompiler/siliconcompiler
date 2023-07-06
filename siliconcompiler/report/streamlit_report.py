import os
import time
import tempfile
import json

try:
    from streamlit.web import bootstrap
except ModuleNotFoundError:
    # In streamlit 1.10.1 bootsrap was moved to streamlit.web
    # This is the only version available for Python 3.6
    from streamlit import bootstrap

from streamlit import config as _config

import multiprocessing
import subprocess
import atexit
import shutil


class Dashboard():
    def __init__(self, chip, port=8501):
        self.__dashboard = None
        self.__chip = chip
        self.__directory = tempfile.mkdtemp(prefix='sc_dashboard_',
                                            suffix=f'_{self.__chip.design}')
        self.__manifest = os.path.join(self.__directory, 'manifest.json')
        self.__port = port
        dirname = os.path.dirname(__file__)
        self.__streamlit_file = os.path.join(dirname, 'Home.py')

        self.__streamlit_args = [
            ("browser.gatherUsageStats", False),
            ("browser.serverPort", self.__port),
            ("logger.level", 'error'),
            ("runner.fastReruns", True),
            ("server.port", self.__port)
        ]

        self.__config = {"manifest": self.__manifest}

        self.__sleep_time = 0.5

        atexit.register(self.__cleanup)

    def open_dashboard(self):
        with open(self.__get_config_file(), 'w') as f:
            json.dump(self.__config, f, indent=4)

        self.update_manifest()

        self.__dashboard = multiprocessing.Process(
            target=self._run_streamlit_bootstrap)

        self.__dashboard.start()

    def update_manifest(self):
        self.__chip.write_manifest(self.__manifest, prune=False)

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

    def stop(self):
        if not self.is_running():
            return

        while self.__dashboard.is_alive():
            self.__dashboard.terminate()
            self._sleep()

        self.__dashboard = None
        self.__manifest = None

    def wait(self):
        self.__dashboard.join()

    def _sleep(self):
        time.sleep(self.__sleep_time)

    def _run_streamlit_bootstrap(self):
        for config, val in self.__streamlit_args:
            _config.set_option(config, val)

        bootstrap.run(self.__streamlit_file,
                      '',
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
