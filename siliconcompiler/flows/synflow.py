from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.opensta import timing

from siliconcompiler.tools.builtin import minimum

from siliconcompiler import Flowgraph
from siliconcompiler.tools.slang import elaborate


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

    def __init__(self, name: str = "synflow", syn_np: int = 1, timing_np: int = 1):
        """
        Initializes the SynthesisFlowgraph.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch. If
                greater than 1, a 'minimum' step is added to select the best
                result.
            * timing_np (int): The number of parallel timing analysis jobs to
                launch.
        """
        super().__init__()
        self.set_name(name)

        self.node("elaborate", elaborate.Elaborate())
        if syn_np > 1:
            self.node("synmin", minimum.MinimumTask())

        for n in range(syn_np):
            self.node("synthesis", syn_asic.ASICSynthesis(), index=n)
            self.edge("elaborate", "synthesis", head_index=n)

            if syn_np > 1:
                self.edge("synthesis", "synmin", tail_index=n)

            for metric in ('errors',):
                self.set("synthesis", str(n), 'goal', metric, 0)

        if syn_np > 1:
            prev_step = "synmin"
        else:
            prev_step = "synthesis"
        for n in range(timing_np):
            self.node("timing", timing.TimingTask(), index=n)
            self.edge(prev_step, "timing", head_index=n)

    @classmethod
    def make_docs(cls):
        return SynthesisFlow(syn_np=3, timing_np=3)


##################################################
if __name__ == "__main__":
    flow = SynthesisFlow(syn_np=3, timing_np=3)
    flow.write_flowgraph(f"{flow.name}.png")
