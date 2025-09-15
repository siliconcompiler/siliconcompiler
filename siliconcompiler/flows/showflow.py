from siliconcompiler import Flowgraph
from siliconcompiler.tool import ShowTaskSchema


class ShowFlow(Flowgraph):
    """A minimal flow to display a design file using its associated viewer.

    This flow is automatically generated and consists of a single node that
    runs a specific 'show' or 'screenshot' task for a given file format (e.g.,
    GDS, DEF).
    """
    def __init__(self, task: ShowTaskSchema):
        """
        Initializes the ShowFlow with a single task.

        Args:
            task (ShowTaskSchema): The specific show/screenshot task to be executed.
        """
        super().__init__()
        self.set_name("showflow")

        self.node(task.task(), task)

    @classmethod
    def make_docs(cls):
        from siliconcompiler.tools.klayout.show import ShowTask
        return ShowFlow(ShowTask())


##################################################
if __name__ == "__main__":
    from siliconcompiler import ShowTaskSchema
    flow = ShowFlow(ShowTaskSchema.get_task("gds"))
    flow.write_flowgraph(f"{flow.name}.png")
