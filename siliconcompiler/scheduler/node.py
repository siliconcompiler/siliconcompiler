import multiprocessing


class SchedulerNode:
    def __init__(self, step, index, chip, task, logger):
        self.__step = step
        self.__index = index
        self.__chip = chip
        self.__task = task
        self.__logger = logger

        self.__state = None

        self.__parent_pipe, self.__child_pipe = multiprocessing.Pipe()
        self.set_queue(None)

    @property
    def pipe(self):
        return self.__parent_pipe

    def set_queue(self, queue):
        self.__proc_queue = queue

    def reset(self):
        pass

    def clean(self):
        pass

    def setup(self):
        pass

    def requires_run(self, old_node=None):
        pass

    def run(self):
        pass
