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

    Proves that two views of a design implement the same logic: either two
    gate-level netlists, or a netlist against the RTL it was synthesized from.

    The flow consists of the following step:
        * **lec**: Checks the two netlists against each other. The sequential
          check is named **sec** instead.

    This flow holds only the check, not the steps which build what it checks:
    the views it compares are read from the nodes feeding the check node, so
    instantiate it inside a flow which emits them
    (:meth:`~siliconcompiler.Flowgraph.graph`) and connect those nodes to it.
    Synthesis does not re-emit the RTL it consumed, so a check against RTL takes
    that edge from elaboration rather than from synthesis.

    Supported tools:

        * 'kepler': a combinational check of two netlists with Kepler-formal.
        * 'kepler-sec': Kepler-formal's sequential engine, which checks a
          netlist against the RTL it was synthesized from.
        * 'yosys': a k-induction check with Yosys, which reads two netlists when
          both are present and otherwise the netlist against the RTL.
    '''

    def __init__(self, name: Optional[str] = None, tool: str = "kepler"):
        """
        Initializes the LECFlow.

        Args:
            name (str, optional): The name of the flow. Defaults to
                'lecflow-<tool>'.
            tool (str): The equivalence check to run. Supported options are
                'kepler', 'kepler-sec' and 'yosys'.

        Raises:
            ValueError: If an unsupported tool is specified.
        """
        if name is None:
            name = f"lecflow-{tool}"
        super().__init__(name)

        if tool == "kepler":
            self.node("lec", KeplerLECTask())
        elif tool == "kepler-sec":
            self.node("sec", KeplerSECTask())
        elif tool == "yosys":
            self.node("lec", YosysLECTask())
        else:
            raise ValueError(f'{tool} is not a supported tool')

    @classmethod
    def make_docs(cls):
        return [cls(tool="kepler"),
                cls(tool="kepler-sec"),
                cls(tool="yosys")]


##################################################
if __name__ == "__main__":
    for flowcls in [PropertyCheckFlow, LECFlow]:
        flow = flowcls()
        flow.write_flowgraph(f"{flow.name}.png")
