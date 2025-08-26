from siliconcompiler.tools.magic import extspice
from siliconcompiler.tools.magic import drc
from siliconcompiler.tools.netgen import lvs
from siliconcompiler.tools.builtin import join

from siliconcompiler import FlowgraphSchema


class SignoffFlow(FlowgraphSchema):
    '''
    A flow for running LVS/DRC signoff on a GDS layout.
    '''

    def __init__(self, name: str = "signoffflow"):
        super().__init__(name)

        self.node("drc", drc.DRCTask())

        self.node("extspice", extspice.ExtractTask())
        self.node("lvs", lvs.LVSTask())
        self.edge("extspice", "lvs")

        self.node("signoff", join.JoinTask())
        self.edge("drc", "signoff")
        self.edge("lvs", "signoff")


##################################################
if __name__ == "__main__":
    flow = SignoffFlow()
    flow.write_flowgraph(f"{flow.name}.png")
