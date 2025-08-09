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
        self.__start = datetime.now()
        self.__error = False

        # Parent logger
        now_file = self.__start.strftime("%Y-%m-%d-%H-%M-%S-%f")
        self.__logfile = os.path.join(tempfile.gettempdir(),
                                      "siliconcompiler",
                                      f"{now_file}_{id(self)}.log")
        self._init_logger()

        # Manager to thread data
        self.__manager = multiprocessing.Manager()

        atexit.register(self.stop)

    def _init_logger(self):
        # Root logger
        self.__logger = logging.getLogger("siliconcompiler")
        self.__logger.propagate = False

        if self.__ENABLE_LOGGER:
            self.__logger.setLevel(logging.INFO)
            try:
                os.makedirs(os.path.dirname(self.__logfile), exist_ok=True)

                handler = logging.FileHandler(self.__logfile)
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s | %(name)s | %(levelname)s | %(message)s'))
                handler.setLevel(logging.INFO)

                self.__logger.addHandler(handler)

                now_print = self.__start.strftime("%Y-%m-%d %H:%M:%S.%f")
                self.__logger.info(f"Log started at {now_print}")

                handler.setLevel(logging.WARNING)
            except:  # noqa E722
                pass

    def stop(self):
        # Remove all logger handlers
        for handler in list(self.__logger.handlers):
            self.__logger.removeHandler(handler)
        if not self.__error:
            try:
                os.remove(self.__logfile)
            except:  # noqa E722
                pass

        self.__manager.shutdown()

    @staticmethod
    def error(msg: str = None):
        if msg:
            MPManager().logger().error(f"Error: {msg}")
        else:
            MPManager().logger().error("Error occurred")
        MPManager().__error = True

    @staticmethod
    def get_manager():
        return MPManager().__manager

    @staticmethod
    def logger() -> logging.Logger:
        return MPManager().__logger
