from siliconcompiler import FlowgraphSchema


class ShowFlow(FlowgraphSchema):
    """
    Small auto created flow to build a single node show/screenshot flow
    """
    def __init__(self, task):
        super().__init__()
        self.set_name("showflow")

        self.node(task.task(), task)


##################################################
if __name__ == "__main__":
    from siliconcompiler import ShowTaskSchema
    flow = ShowFlow(ShowTaskSchema.get_task("gds"))
    flow.write_flowgraph(f"{flow.name}.png")
