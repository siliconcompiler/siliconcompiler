from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.yosys import syn_fpga as yosys_syn
from siliconcompiler.tools.vpr import place as vpr_place
from siliconcompiler.tools.vpr import route as vpr_route
from siliconcompiler.tools.genfasm import bitstream as genfasm_bitstream
from siliconcompiler.tools.opensta import timing

from siliconcompiler.tools.vivado import syn_fpga as vivado_syn
from siliconcompiler.tools.vivado import place as vivado_place
from siliconcompiler.tools.vivado import route as vivado_route
from siliconcompiler.tools.vivado import bitstream as vivado_bitstream

from siliconcompiler.tools.nextpnr import apr as nextpnr_apr

from siliconcompiler.flows.elaborationflow import ElaborationFlow


class FPGAXilinxFlow(Flowgraph):
    '''An FPGA compilation flow targeting Xilinx devices using Vivado.

    This flow uses the commercial Vivado toolchain for synthesis, placement,
    routing, and bitstream generation.

    The flow consists of the following steps:

        * **elaborate**: Elaborate the RTL design from sources.
        * **syn_fpga**: Synthesize RTL into a device-specific netlist.
        * **place**: Place the synthesized netlist onto the FPGA fabric.
        * **route**: Route the connections between placed components.
        * **bitstream**: Generate the final bitstream for device programming.
    '''
    def __init__(self, name: Optional[str] = None, language: str = "verilog"):
        """
        Initializes the FPGAXilinxFlow.

        Args:
            name (str, optional): The name of the flow. If not provided, it
                defaults to 'fpgaflow-xilinx-<language>'.
            language (str): The hardware description language of the design.
        """
        if name is None:
            name = f"fpgaflow-xilinx-{language}"
        super().__init__(name)

        elab = ElaborationFlow(language=language)
        self.graph(elab)
        elab_node = elab.get_exit_nodes()
        if len(elab_node) != 1:
            raise ValueError("Elaboration flow must have exactly one exit node.")
        elab_node = elab_node[0][0]  # Get the node name from the tuple

        self.node("syn_fpga", vivado_syn.SynthesisTask())
        self.edge(elab_node, "syn_fpga")
        self.node("place", vivado_place.PlaceTask())
        self.edge("syn_fpga", "place")
        self.node("route", vivado_route.RouteTask())
        self.edge("place", "route")
        self.node("bitstream", vivado_bitstream.BitstreamTask())
        self.edge("route", "bitstream")

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create representative instances of the flow, one for each supported
        source language.

        Returns:
            A list of instances of the FPGAXilinxFlow class.
        '''
        return [
            cls(language="verilog"),
            cls(language="systemverilog-sv2v"),
            cls(language="chisel"),
            cls(language="vhdl"),
            cls(language="hls"),
            cls(language="bluespec")
        ]


class FPGANextPNRFlow(Flowgraph):
    '''An open-source FPGA flow using Yosys and NextPNR.

    This flow is tailored for FPGAs supported by the NextPNR tool, which
    handles placement, routing, and bitstream generation in a single step.

    The flow consists of the following steps:

        * **elaborate**: Elaborate the RTL design from sources.
        * **syn_fpga**: Synthesize RTL into a device-specific netlist using Yosys.
        * **apr**: Perform automatic place and route (APR) and generate the
                   bitstream using NextPNR.
    '''
    def __init__(self, name: Optional[str] = None, language: str = "verilog"):
        """
        Initializes the FPGANextPNRFlow.

        Args:
            name (str, optional): The name of the flow. If not provided, it
                defaults to 'fpgaflow-nextpnr-<language>'.
            language (str): The hardware description language of the design.
        """
        if name is None:
            name = f"fpgaflow-nextpnr-{language}"
        super().__init__(name)

        elab = ElaborationFlow(language=language)
        self.graph(elab)
        elab_node = elab.get_exit_nodes()
        if len(elab_node) != 1:
            raise ValueError("Elaboration flow must have exactly one exit node.")
        elab_node = elab_node[0][0]  # Get the node name from the tuple

        self.node("syn_fpga", yosys_syn.FPGASynthesis())
        self.edge(elab_node, "syn_fpga")
        self.node("apr", nextpnr_apr.APRTask())
        self.edge("syn_fpga", "apr")

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create representative instances of the flow, one for each supported
        source language.

        Returns:
            A list of instances of the FPGANextPNRFlow class.
        '''
        return [
            cls(language="verilog"),
            cls(language="systemverilog-sv2v"),
            cls(language="chisel"),
            cls(language="vhdl"),
            cls(language="hls"),
            cls(language="bluespec")
        ]


class FPGAVPRFlow(Flowgraph):
    '''An open-source FPGA flow using Yosys, VPR, and GenFasm.

    This flow is designed for academic and research FPGAs, utilizing VPR
    (Versatile Place and Route) for placement and routing.

    The flow consists of the following steps:

        * **elaborate**: Elaborate the RTL design from sources.
        * **synthesis**: Synthesize the elaborated design into a netlist using Yosys.
        * **place**: Place the netlist components onto the FPGA architecture using VPR.
        * **route**: Route the connections between placed components using VPR.
        * **bitstream**: Generate the final bitstream using GenFasm.
    '''
    def __init__(self, name: Optional[str] = None, language: str = "verilog"):
        """
        Initializes the FPGAVPRFlow.

        Args:
            name (str, optional): The name of the flow. If not provided, it
                defaults to 'fpgaflow-vpr-<language>'.
            language (str): The hardware description language of the design.
        """
        if name is None:
            name = f"fpgaflow-vpr-{language}"
        super().__init__(name)

        elab = ElaborationFlow(language=language)
        self.graph(elab)
        elab_node = elab.get_exit_nodes()
        if len(elab_node) != 1:
            raise ValueError("Elaboration flow must have exactly one exit node.")
        elab_node = elab_node[0][0]  # Get the node name from the tuple

        self.node("synthesis", yosys_syn.FPGASynthesis())
        self.edge(elab_node, "synthesis")
        self.node("place", vpr_place.PlaceTask())
        self.edge("synthesis", "place")
        self.node("route", vpr_route.RouteTask())
        self.edge("place", "route")
        self.node("bitstream", genfasm_bitstream.BitstreamTask())
        self.edge("route", "bitstream")

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create representative instances of the flow, one for each supported
        source language.

        Returns:
            A list of instances of the FPGAVPRFlow class.
        '''
        return [
            cls(language="verilog"),
            cls(language="systemverilog-sv2v"),
            cls(language="chisel"),
            cls(language="vhdl"),
            cls(language="hls"),
            cls(language="bluespec")
        ]


class FPGAVPROpenSTAFlow(FPGAVPRFlow):
    '''An open-source FPGA flow using Yosys, VPR, GenFasm, and OpenSTA.

    This flow is designed for academic and research FPGAs, utilizing VPR
    (Versatile Place and Route) for placement and routing and OpenSTA for
    post-implementation timing analysis.

    The flow consists of the following steps:

        * **elaborate**: Elaborate the RTL design from sources.
        * **synthesis**: Synthesize the elaborated design into a netlist using Yosys.
        * **place**: Place the netlist components onto the FPGA architecture using VPR.
        * **route**: Route the connections between placed components using VPR.
        * **bitstream**: Generate the final bitstream using GenFasm.
        * **timing**: Perform post-implementation static timing analysis of the design.
    '''
    def __init__(self, name: Optional[str] = None, language: str = "verilog"):
        """
        Initializes the FPGAVPROpenSTAFlow.

        Args:
            name (str, optional): The name of the flow. If not provided, it
                defaults to 'fpgaflow-vpr-open-sta-<language>'.
            language (str): The hardware description language of the design.
        """
        if name is None:
            name = f"fpgaflow-vpr-open-sta-{language}"
        super().__init__(name, language=language)

        self.node("timing", timing.FPGATimingTask())
        self.edge("route", "timing")

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create representative instances of the flow, one for each supported
        source language.

        Returns:
            A list of instances of the FPGAVPROpenSTAFlow class.
        '''
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
    for flow in [FPGANextPNRFlow(), FPGAVPRFlow(), FPGAXilinxFlow()]:
        flow.write_flowgraph(f"{flow.name}.png")
