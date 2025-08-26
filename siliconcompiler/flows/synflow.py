from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.opensta import timing

from siliconcompiler.tools.builtin import minimum

from siliconcompiler import FlowgraphSchema
from siliconcompiler.tools.slang import elaborate


class SynthesisFlowgraph(FlowgraphSchema):
    '''
    A configurable ASIC synthesis flow with static timing.

    The 'synflow' includes the stages below. The steps syn have
    minimization associated with them.
    To view the flowgraph, see the .png file.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Translates RTL to netlist using Yosys
    * **timing**: Create timing reports of design

    The syn and timing steps supports per process
    options that can be set up by setting 'syn_np' or 'timing_np'
    arg to a value > 1, as detailed below:

    * syn_np : Number of parallel synthesis jobs to launch
    * timing_np : Number of parallel timing jobs to launch
    '''
    def __init__(self, name: str = "synflow", syn_np: int = 1, timing_np: int = 1):
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


##################################################
if __name__ == "__main__":
    flow = SynthesisFlowgraph(syn_np=3, timing_np=3)
    flow.write_flowgraph(f"{flow.name}.png")
