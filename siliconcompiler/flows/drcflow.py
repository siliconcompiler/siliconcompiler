from siliconcompiler import FlowgraphSchema
from siliconcompiler.tools.klayout import drc


class DRCFlow(FlowgraphSchema):
    '''
    Perform a DRC run on an input GDS
    '''
    def __init__(self, name: str = "drcflow"):
        super().__init__(name)

        self.node("drc", drc.DRCTask())


##################################################
if __name__ == "__main__":
    flow = DRCFlow()
    flow.write_flowgraph(f"{flow.name}.png")
