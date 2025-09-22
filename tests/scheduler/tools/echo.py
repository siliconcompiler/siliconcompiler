from siliconcompiler import Task


class EchoTask(Task):
    def __init__(self):
        super().__init__()

    def tool(self):
        return "echo"

    def task(self):
        return "echo"
