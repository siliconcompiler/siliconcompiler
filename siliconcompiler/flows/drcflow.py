from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.klayout.drc import DRCTask as KlayoutDRC
from siliconcompiler.tools.magic.drc import DRCTask as MagicDRC


class DRCFlow(Flowgraph):
    '''A design rule check (DRC) flow.

    This flow is designed to perform a DRC run on an input GDSII file using
    KLayout or Magic.
    '''
    def __init__(self, name: Optional[str] = None, tool: str = "klayout"):
        """
        Initializes the DRCFlow.

        Args:
            * name (str): The name of the flow.
            * tool (str): The DRC tool to use. Supported options are 'klayout' and 'magic'.

        Raises:
            ValueError: If an unsupported tool is specified.
        """
        if name is None:
            name = f"drcflow-{tool}"
        super().__init__(name)

        if tool == "klayout":
            self.graph(KlayoutDRCFlow())
        elif tool == "magic":
            self.graph(MagicDRCFlow())
        else:
            raise ValueError(f'{tool} is not a supported tool')

    @classmethod
    def make_docs(cls):
        return [cls(tool="klayout"),
                cls(tool="magic")]


class KlayoutDRCFlow(Flowgraph):
    '''A KLayout-based design rule check (DRC) flow.

    This flow is designed to perform a DRC run on an input GDSII file using
    KLayout.
    '''
    def __init__(self, name: str = "klayoutdrcflow"):
        """
        Initializes the KLayoutDRCFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("drc", KlayoutDRC())


class MagicDRCFlow(Flowgraph):
    '''A Magic-based design rule check (DRC) flow.

    This flow is designed to perform a DRC run on an input GDSII file using
    Magic.
    '''
    def __init__(self, name: str = "magicdrcflow"):
        """
        Initializes the MagicDRCFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("drc", MagicDRC())


##################################################
if __name__ == "__main__":
    flow = DRCFlow()
    flow.write_flowgraph(f"{flow.name}.png")
