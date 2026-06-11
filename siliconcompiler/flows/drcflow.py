from siliconcompiler import Flowgraph
from siliconcompiler.tools.klayout import drc as klayout_drc
from siliconcompiler.tools.magic import drc as magic_drc


class DRCFlow(Flowgraph):
    '''A design rule check (DRC) flow.

    This flow is designed to perform a DRC run on an input GDSII file using
    KLayout.
    '''
    def __init__(self, name: str = "drcflow", tool: str = "klayout"):
        """
        Initializes the DRCFlow.

        Args:
            * name (str): The name of the flow.
            * tool (str): The DRC tool to use. Supported options are 'klayout' and 'magic'.

        Raises:
            ValueError: If an unsupported tool is specified.
        """
        super().__init__(name)

        if tool == "klayout":
            self.node("drc", klayout_drc.DRCTask())
        elif tool == "magic":
            self.node("drc", magic_drc.DRCTask())
        else:
            raise ValueError(f'{tool} is not a supported tool')


##################################################
if __name__ == "__main__":
    flow = DRCFlow()
    flow.write_flowgraph(f"{flow.name}.png")
