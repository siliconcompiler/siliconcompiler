from enum import Flag, auto
from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.sby.bmc import BMCTask
from siliconcompiler.tools.sby.prove import ProveTask
from siliconcompiler.tools.sby.cover import CoverTask

from siliconcompiler.tools.keplerformal.lec import LECTask as KeplerLECTask
from siliconcompiler.tools.keplerformal.sec import SECTask as KeplerSECTask
from siliconcompiler.tools.yosys.lec_asic import ASICLECTask as YosysLECTask


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
            raise ValueError("requires at least one mode")

    @classmethod
    def make_docs(cls):
        return cls(modes=PropertyCheckMode.BMC |
                   PropertyCheckMode.PROVE |
                   PropertyCheckMode.COVER)


class LECFlow(Flowgraph):
    '''A logical equivalence check (LEC) flow.

    Proves that two gate-level netlists implement the same logic.

    The flow consists of the following step:
        * **lec**: Checks the two netlists against each other.

    This flow holds only the check, not the steps which build what it checks:
    the netlists it compares are read from the nodes feeding the **lec** node,
    so instantiate it inside a flow which emits them
    (:meth:`~siliconcompiler.Flowgraph.graph`) and connect those nodes to it.

    Supported tools:

        * 'kepler-formal': a combinational equivalence check with Kepler-formal.
        * 'yosys': a k-induction equivalence check with Yosys.
    '''

    def __init__(self, name: Optional[str] = None, tool: str = "kepler-formal"):
        """
        Initializes the LECFlow.

        Args:
            name (str, optional): The name of the flow. Defaults to
                'lecflow-<tool>'.
            tool (str): The equivalence checking tool to use. Supported options
                are 'kepler-formal' and 'yosys'.

        Raises:
            ValueError: If an unsupported tool is specified.
        """
        if name is None:
            name = f"lecflow-{tool}"
        super().__init__(name)

        if tool == "kepler-formal":
            self.node("lec", KeplerLECTask())
        elif tool == "yosys":
            self.node("lec", YosysLECTask())
        else:
            raise ValueError(f'{tool} is not a supported tool')

    @classmethod
    def make_docs(cls):
        return [cls(tool="kepler-formal"),
                cls(tool="yosys")]


class SECFlow(Flowgraph):
    '''A sequential equivalence check (SEC) flow.

    Proves that a gate-level netlist implements the same logic as the RTL it was
    synthesized from.

    The flow consists of the following step:
        * **sec**: Checks the netlist against the RTL.

    Like :class:`LECFlow`, this flow holds only the check: the RTL and the
    netlist are read from the nodes feeding the **sec** node, so instantiate it
    inside a flow which emits them (:meth:`~siliconcompiler.Flowgraph.graph`)
    and connect those nodes to it. The RTL edge comes from elaboration rather
    than synthesis, since synthesis does not re-emit what it consumed.

    Supported tools:

        * 'kepler-formal': a sequential equivalence check with Kepler-formal.
        * 'yosys': a k-induction equivalence check with Yosys.
    '''

    def __init__(self, name: Optional[str] = None, tool: str = "kepler-formal"):
        """
        Initializes the SECFlow.

        Args:
            name (str, optional): The name of the flow. Defaults to
                'secflow-<tool>'.
            tool (str): The equivalence checking tool to use. Supported options
                are 'kepler-formal' and 'yosys'.

        Raises:
            ValueError: If an unsupported tool is specified.
        """
        if name is None:
            name = f"secflow-{tool}"
        super().__init__(name)

        if tool == "kepler-formal":
            self.node("sec", KeplerSECTask())
        elif tool == "yosys":
            self.node("sec", YosysLECTask())
        else:
            raise ValueError(f'{tool} is not a supported tool')

    @classmethod
    def make_docs(cls):
        return [cls(tool="kepler-formal"),
                cls(tool="yosys")]


##################################################
if __name__ == "__main__":
    for flowcls in [PropertyCheckFlow, LECFlow, SECFlow]:
        flow = flowcls()
        flow.write_flowgraph(f"{flow.name}.png")
