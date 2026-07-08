from enum import Flag, auto
from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.sby.bmc import BMCTask
from siliconcompiler.tools.sby.prove import ProveTask
from siliconcompiler.tools.sby.cover import CoverTask


class PropertyCheckMode(Flag):
    '''Formal property-checking modes.

    Combine with the bitwise-or operator to run several in parallel, e.g.
    ``PropertyCheckMode.BMC | PropertyCheckMode.COVER``.

    Attributes:
        BMC: bounded model check of all assertions.
        PROVE: unbounded proof via k-induction.
        COVER: reachability check of all cover statements.
    '''
    BMC = auto()
    PROVE = auto()
    COVER = auto()


class PropertyCheckFlow(Flowgraph):
    '''A formal property verification flow.

    Checks the SVA properties embedded in the RTL source files using
    SymbiYosys (sby) on top of Yosys and an SMT solver. Each selected
    :class:`PropertyCheckMode` runs as its own parallel node, so several checks
    (e.g. a bmc proof plus a cover reachability/vacuity check) can run together
    in a single job.
    '''

    _MODE_TASKS = {
        PropertyCheckMode.BMC: BMCTask,
        PropertyCheckMode.PROVE: ProveTask,
        PropertyCheckMode.COVER: CoverTask,
    }

    def __init__(self, name: Optional[str] = None,
                 modes: PropertyCheckMode = PropertyCheckMode.BMC):
        """
        Initializes the PropertyCheckFlow.

        Args:
            name (str, optional): The name of the flow. Defaults to
                'propertycheckflow'.
            modes (PropertyCheckMode): One or more modes to run, combined with
                the bitwise-or operator. Each selected mode is added as a
                parallel node named after the mode ('bmc', 'prove', 'cover').

        Raises:
            ValueError: If no mode is selected.
        """
        if name is None:
            name = "propertycheckflow"
        super().__init__(name)

        added = False
        for mode, taskcls in self._MODE_TASKS.items():
            if mode in modes:
                self.node(mode.name.lower(), taskcls())
                added = True

        if not added:
            raise ValueError("PropertyCheckFlow requires at least one mode")

    @classmethod
    def make_docs(cls):
        return cls(modes=PropertyCheckMode.BMC |
                   PropertyCheckMode.PROVE |
                   PropertyCheckMode.COVER)


##################################################
if __name__ == "__main__":
    flow = PropertyCheckFlow()
    flow.write_flowgraph(f"{flow.name}.png")
