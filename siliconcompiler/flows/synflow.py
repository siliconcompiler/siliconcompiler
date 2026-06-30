from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.opensta import timing

from siliconcompiler.tools.builtin import minimum

from siliconcompiler import Flowgraph

from siliconcompiler.flows.elaborationflow import ElaborationFlow, SV2VElaborationFlow, \
    HLSElaborationFlow, VHDLElaborationFlow, ChiselElaborationFlow


class _SynthesisFlowBase(Flowgraph):
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

    def _elaborate(self) -> Flowgraph:
        raise NotImplementedError("This method should be implemented by subclasses.")

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

        elab = self._elaborate()
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
        return cls(syn_np=3, timing_np=3)


class SynthesisFlow(_SynthesisFlowBase):
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

    def _elaborate(self):
        return ElaborationFlow()

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
        super().__init__(name, syn_np=syn_np, timing_np=timing_np)


class SV2VSynthesisFlow(_SynthesisFlowBase):
    '''A SystemVerilog-to-Verilog extension of the ASICFlow.

    This flow is intended for designs written in SystemVerilog that may not be
    fully supported by downstream synthesis or APR tools. It inserts a
    'convert' step using SV2V before the standard 'elaborate' step to ensure
    the design is in a compatible Verilog format.
    '''

    def _elaborate(self):
        return SV2VElaborationFlow()

    def __init__(self, name: str = "sv2vsynflow", syn_np: int = 1, timing_np: int = 1):
        """
        Initializes the SV2VSynthesisFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch. If
                greater than 1, a 'minimum' step is added to select the best
                result.
            * timing_np (int): The number of parallel timing analysis jobs to
                launch.
        """
        super().__init__(name, syn_np=syn_np, timing_np=timing_np)


class HLSSynthesisFlow(_SynthesisFlowBase):
    '''A High-Level Synthesis (HLS) extension of the ASICFlow.

    This class inherits from ASICFlow and modifies it to support C-based HLS.
    It replaces the initial 'elaborate' step with a 'convert' step, which
    handles the conversion of HLS C code to RTL using the Bambu tool.
    '''

    def _elaborate(self):
        return HLSElaborationFlow()

    def __init__(self, name: str = "hlssynflow", syn_np: int = 1, timing_np: int = 1):
        """
        Initializes the HLSSynthesisFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch. If
                greater than 1, a 'minimum' step is added to select the best
                result.
            * timing_np (int): The number of parallel timing analysis jobs to
                launch.
        """
        super().__init__(name, syn_np=syn_np, timing_np=timing_np)


class VHDLSynthesisFlow(_SynthesisFlowBase):
    '''A VHDL-based ASIC synthesis flow.

    This class extends the standard ASICFlow to support VHDL input by
    replacing the initial Verilog-focused 'elaborate' step with a 'convert'
    step. This new step uses GHDL to analyze and elaborate the VHDL design
    before synthesis.
    '''

    def _elaborate(self):
        return VHDLElaborationFlow()

    def __init__(self, name: str = "vhdlsynflow", syn_np: int = 1, timing_np: int = 1):
        """
        Initializes the VHDLSynthesisFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch. If
                greater than 1, a 'minimum' step is added to select the best
                result.
            * timing_np (int): The number of parallel timing analysis jobs to
                launch.
        """
        super().__init__(name, syn_np=syn_np, timing_np=timing_np)


class ChiselSynthesisFlow(_SynthesisFlowBase):
    '''A Chisel-based ASIC synthesis flow.

    This class extends the standard ASICFlow to support designs written in
    the Chisel hardware construction language. It replaces the Verilog-focused
    'elaborate' step with a 'convert' step that uses the Chisel compiler to
    generate Verilog from the Chisel source before synthesis.
    '''

    def _elaborate(self):
        return ChiselElaborationFlow()

    def __init__(self, name: str = "chiselsynflow", syn_np: int = 1, timing_np: int = 1):
        """
        Initializes the ChiselSynthesisFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch. If
                greater than 1, a 'minimum' step is added to select the best
                result.
            * timing_np (int): The number of parallel timing analysis jobs to
                launch.
        """
        super().__init__(name, syn_np=syn_np, timing_np=timing_np)


##################################################
if __name__ == "__main__":
    for flowcls in [SynthesisFlow,
                    SV2VSynthesisFlow,
                    HLSSynthesisFlow,
                    VHDLSynthesisFlow,
                    ChiselSynthesisFlow]:
        flow = flowcls(syn_np=3, timing_np=3)
        flow.write_flowgraph(f"{flow.name}.png")
