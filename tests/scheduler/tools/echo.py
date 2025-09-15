from siliconcompiler.tool import TaskSchema


class EchoTask(TaskSchema):
    def __init__(self):
        super().__init__()

    def tool(self):
        return "echo"

    def task(self):
        return "echo"
