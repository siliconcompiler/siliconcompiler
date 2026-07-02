from siliconcompiler import Flowgraph

from siliconcompiler.tools.magic import extspice
from siliconcompiler.tools.netgen import lvs


class MagicLVSFlow(Flowgraph):
    '''A flow for running LVS signoff on a GDS layout.

    This flow performs a key physical verification step:

        1. Layout Versus Schematic (LVS) checking using Netgen.

    The LVS step first requires extracting a SPICE netlist from the layout,
    which is also handled by Magic.
    '''

    def __init__(self, name: str = "magiclvsflow"):
        """
        Initializes the MagicLVSFlow.

        Args:
            name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("extspice", extspice.ExtractTask())
        self.node("lvs", lvs.LVSTask())
        self.edge("extspice", "lvs")


##################################################
if __name__ == "__main__":
    flow = MagicLVSFlow()
    flow.write_flowgraph(f"{flow.name}.png")
