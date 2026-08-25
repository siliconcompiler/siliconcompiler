from enum import Flag, auto
from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.sby.bmc import BMCTask
from siliconcompiler.tools.sby.prove import ProveTask
from siliconcompiler.tools.sby.cover import CoverTask

from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.keplerformal import sec

from siliconcompiler.flows.elaborationflow import ElaborationFlow


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

    This flow synthesizes an RTL design into a gate-level netlist and then
    proves that the netlist implements the same logic as the RTL it was
    synthesized from.

    The flow consists of the following steps:
        * **elaborate**: Elaborates the RTL design from its source files.
        * **synthesis**: Translates the elaborated RTL into a gate-level netlist
                         using Yosys.
        * **lec**: Checks the gate-level netlist against the elaborated RTL
                   using Kepler-formal.

    The **lec** step reads the RTL from **elaborate**, since **synthesis**
    does not re-emit what it consumed.
    '''

    def __init__(self, name: Optional[str] = None, language: str = "verilog"):
        """
        Initializes the LECFlow.

        Args:
            name (str, optional): The name of the flow. Defaults to
                'lecflow-<language>'.
            language (str): The hardware description language of the design.
        """
        if name is None:
            name = f"lecflow-{language}"
        super().__init__(name)

        elab = ElaborationFlow(language=language)
        self.graph(elab)

        elab_node = elab.get_exit_nodes()
        if len(elab_node) != 1:
            raise ValueError("Elaboration flow must have exactly one exit node.")
        elab_node = elab_node[0][0]  # Get the node name from the tuple

        self.node("synthesis", syn_asic.ASICSynthesis())
        self.edge(elab_node, "synthesis")

        self.node("lec", sec.SECTask())
        self.edge(elab_node, "lec")
        self.edge("synthesis", "lec")

    @classmethod
    def make_docs(cls):
        return [
            cls(language="verilog"),
            cls(language="systemverilog-sv2v"),
            cls(language="chisel"),
            cls(language="vhdl"),
            cls(language="hls"),
            cls(language="bluespec")
        ]


##################################################
if __name__ == "__main__":
    for flowcls in [PropertyCheckFlow, LECFlow]:
        flow = flowcls()
        flow.write_flowgraph(f"{flow.name}.png")
