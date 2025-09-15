from siliconcompiler import Flowgraph
from siliconcompiler.tools.klayout import drc


class DRCFlow(Flowgraph):
    '''A design rule check (DRC) flow.

    This flow is designed to perform a DRC run on an input GDSII file using
    KLayout.
    '''
    def __init__(self, name: str = "drcflow"):
        """
        Initializes the DRCFlow.

        Args:
            name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("drc", drc.DRCTask())


##################################################
if __name__ == "__main__":
    flow = DRCFlow()
    flow.write_flowgraph(f"{flow.name}.png")
