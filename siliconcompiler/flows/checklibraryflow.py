from siliconcompiler import Flowgraph

from siliconcompiler.tools.opensta.check_library import CheckLibraryTask


class CheckLibraryFlow(Flowgraph):
    '''A library QA flow.

    This flow reads the timing libraries for the configured target and checks
    that the standard-cell setup used by the synthesis and place-and-route
    tools is valid: it verifies the yosys and openroad helper cells/pins exist
    and have the expected directions, and that the yosys ``abc_clock_multiplier``
    matches the liberty time unit. The derived ``abc_constraint_load`` is
    reported for reference rather than enforced. It also emits a report of every
    library cell and its characteristics (pins, capacitance, drive resistance,
    intrinsic delay).
    '''

    def __init__(self, name: str = "checklibraryflow"):
        """
        Initializes the CheckLibraryFlow.

        Args:
            name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("check", CheckLibraryTask())


##################################################
if __name__ == "__main__":
    flow = CheckLibraryFlow()
    flow.write_flowgraph(f"{flow.name}.png")
