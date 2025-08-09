import atexit
import logging
import multiprocessing
import tempfile

import os.path

from datetime import datetime


class _ManagerSingleton(type):
    _instances = {}
    _lock = multiprocessing.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(_ManagerSingleton, cls).__call__(*args, **kwargs)
                cls._instances[cls]._init_singleton()
        return cls._instances[cls]


class MPManager(metaclass=_ManagerSingleton):
    __ENABLE_LOGGER: bool = True

    def __init__(self):
        pass

    def _init_singleton(self):
        # Parent logger
        self.__logger = logging.getLogger("siliconcompiler")
        self.__logger.propagate = False
        if self.__ENABLE_LOGGER:
            self.__logger.setLevel(logging.INFO)
            try:
                log_dir = os.path.join(tempfile.gettempdir(), "siliconcompiler")
                os.makedirs(log_dir, exist_ok=True)
                now = datetime.now()
                now_file = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
                now_print = now.strftime("%Y-%m-%d %H:%M:%S.%f")
                self.__logger.addHandler(logging.FileHandler(
                    os.path.join(log_dir, f"{now_file}_{id(self)}.log")))
                self.__logger.info(f"Log started at {now_print}")
            except:  # noqa E722
                pass

        # Manager to thread data
        self.__manager = multiprocessing.Manager()

        atexit.register(self.stop)

    def stop(self):
        # Remove all logger handlers
        for handler in list(self.__logger.handlers):
            self.__logger.removeHandler(handler)

        self.__manager.shutdown()

    @staticmethod
    def get_manager():
        return MPManager().__manager

    @staticmethod
    def logger() -> logging.Logger:
        return MPManager().__logger
