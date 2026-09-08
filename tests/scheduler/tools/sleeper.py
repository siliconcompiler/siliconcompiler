from siliconcompiler import Task


# Long enough that the process is certainly still there when the test looks for
# it, and distinctive enough to pick out of the process table by command line.
SLEEP_SECONDS = "424242"


class SleepTask(Task):
    """A task whose executable outlives the node running it.

    For tests about what happens to a tool when its node is ended: a task that
    finishes on its own has nothing left to orphan.
    """
    def __init__(self):
        super().__init__()

    def tool(self):
        return "sleep"

    def task(self):
        return "sleep"

    def setup(self):
        super().setup()
        self.set_exe("sleep")
        self.add_commandline_option(SLEEP_SECONDS)
