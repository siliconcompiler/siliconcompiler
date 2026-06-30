from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.opensta import timing

from siliconcompiler.tools.builtin import minimum

from siliconcompiler.flows.elaborationflow import ElaborationFlow


class SynthesisFlow(Flowgraph):
    '''
    A configurable ASIC synthesis flow with static timing analysis.

    This flow translates RTL designs into a gate-level netlist and then
    performs static timing analysis (STA) on the result. It allows for
    parallel execution of both synthesis and timing steps to explore different
    strategies or speed up execution.

    The flow consists of the following steps:
        * **elaborate**: Elaborates the RTL design from its source files.
        * **synthesis**: Translates the elaborated RTL into a gate-level netlist
                         using Yosys.
        * **timing**: Performs static timing analysis on the synthesized netlist
                      using OpenSTA.
    '''

    def __init__(self, name: Optional[str] = None,
                 language: str = "verilog",
                 syn_np: int = 1, timing_np: int = 1):
        """
        Initializes the SynthesisFlow.

        Args:
            * name (str): The name of the flow.
            * language (str): The hardware description language of the design.
            * syn_np (int): The number of parallel synthesis jobs to launch. If
                greater than 1, a 'minimum' step is added to select the best
                result.
            * timing_np (int): The number of parallel timing analysis jobs to
                launch.
        """
        if name is None:
            name = f"synflow-{language}"
        super().__init__(name)

        elab = ElaborationFlow(language=language)
        self.graph(elab)

        elab_node = elab.get_exit_nodes()
        if len(elab_node) != 1:
            raise ValueError("Elaboration flow must have exactly one exit node.")
        elab_node = elab_node[0][0]  # Get the node name from the tuple

        if syn_np > 1:
            self.node("synmin", minimum.MinimumTask())

        for n in range(syn_np):
            self.node("synthesis", syn_asic.ASICSynthesis(), index=n)
            self.edge(elab_node, "synthesis", head_index=n)

            if syn_np > 1:
                self.edge("synthesis", "synmin", tail_index=n)

            for metric in ('errors',):
                self.get_graph_node("synthesis", n).add_goal(metric, 0)

        if syn_np > 1:
            prev_step = "synmin"
        else:
            prev_step = "synthesis"
        for n in range(timing_np):
            self.node("timing", timing.TimingTask(), index=n)
            self.edge(prev_step, "timing", head_index=n)

    @classmethod
    def make_docs(cls):
        return [
            cls(language="verilog", syn_np=3, timing_np=3),
            cls(language="systemverilog-sv2v", syn_np=3, timing_np=3),
            cls(language="chisel", syn_np=3, timing_np=3),
            cls(language="vhdl", syn_np=3, timing_np=3),
            cls(language="hls", syn_np=3, timing_np=3),
            cls(language="bluespec", syn_np=3, timing_np=3)
        ]


##################################################
if __name__ == "__main__":
    for flow in SynthesisFlow.make_docs():
        flow.write_flowgraph(f"{flow.name}.png")
