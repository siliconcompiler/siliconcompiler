from siliconcompiler import Flowgraph

from siliconcompiler.flows.drcflow import MagicDRCFlow
from siliconcompiler.flows.lvsflow import MagicLVSFlow

from siliconcompiler.tools.builtin import join


class SignoffFlow(Flowgraph):
    '''A flow for running LVS/DRC signoff on a GDS layout.

    This flow performs two key physical verification steps in parallel:

        1. Design Rule Checking (DRC) using Magic.
        2. Layout Versus Schematic (LVS) checking using Netgen.

    The LVS step first requires extracting a SPICE netlist from the layout,
    which is also handled by Magic. A final 'join' step ensures that both
    DRC and LVS tasks must complete successfully for the flow to finish.
    '''

    def __init__(self, name: str = "signoffflow"):
        """
        Initializes the SignoffFlow.

        Args:
            name (str): The name of the flow.
        """
        super().__init__(name)

        self.graph(MagicDRCFlow())
        self.graph(MagicLVSFlow())

        self.node("signoff", join.JoinTask())
        self.edge("drc", "signoff")
        self.edge("lvs", "signoff")


##################################################
if __name__ == "__main__":
    flow = SignoffFlow()
    flow.write_flowgraph(f"{flow.name}.png")
