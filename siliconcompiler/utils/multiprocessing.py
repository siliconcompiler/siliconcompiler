import atexit
import multiprocessing


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
    def __init__(self):
        pass

    def _init_singleton(self):
        # Manager to thread data
        self.__manager = multiprocessing.Manager()
        atexit.register(self.stop)

    def stop(self):
        self.__manager.shutdown()

    @staticmethod
    def get_manager():
        return MPManager().__manager
