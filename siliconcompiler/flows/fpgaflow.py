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


from siliconcompiler import Flowgraph
from siliconcompiler.tools.slang import elaborate


class FPGAXilinxFlow(Flowgraph):
    '''An FPGA compilation flow targeting Xilinx devices using Vivado.

    This flow uses the commercial Vivado toolchain for synthesis, placement,
    routing, and bitstream generation.

    The flow consists of the following steps:

        * **syn_fpga**: Synthesize RTL into a device-specific netlist.
        * **place**: Place the synthesized netlist onto the FPGA fabric.
        * **route**: Route the connections between placed components.
        * **bitstream**: Generate the final bitstream for device programming.
    '''
    def __init__(self, name: str = "fpgaflow-xilinx"):
        """
        Initializes the FPGAXilinxFlow.

        Args:
            name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("elaborate", elaborate.Elaborate())
        self.node("syn_fpga", vivado_syn.SynthesisTask())
        self.edge("elaborate", "syn_fpga")
        self.node("place", vivado_place.PlaceTask())
        self.edge("syn_fpga", "place")
        self.node("route", vivado_route.RouteTask())
        self.edge("place", "route")
        self.node("bitstream", vivado_bitstream.BitstreamTask())
        self.edge("route", "bitstream")


class FPGANextPNRFlow(Flowgraph):
    '''An open-source FPGA flow using Yosys and NextPNR.

    This flow is tailored for FPGAs supported by the NextPNR tool, which
    handles placement, routing, and bitstream generation in a single step.

    The flow consists of the following steps:

        * **syn_fpga**: Synthesize RTL into a device-specific netlist using Yosys.
        * **apr**: Perform automatic place and route (APR) and generate the
                   bitstream using NextPNR.
    '''
    def __init__(self, name: str = "fpgaflow-nextpnr"):
        """
        Initializes the FPGANextPNRFlow.

        Args:
            name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("elaborate", elaborate.Elaborate())
        self.node("syn_fpga", yosys_syn.FPGASynthesis())
        self.edge("elaborate", "syn_fpga")
        self.node("apr", nextpnr_apr.APRTask())
        self.edge("syn_fpga", "apr")


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
    def __init__(self, name: str = "fpgaflow-vpr"):
        """
        Initializes the FPGAVPRFlow.

        Args:
            name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("elaborate", elaborate.Elaborate())
        self.node("synthesis", yosys_syn.FPGASynthesis())
        self.edge("elaborate", "synthesis")
        self.node("place", vpr_place.PlaceTask())
        self.edge("synthesis", "place")
        self.node("route", vpr_route.RouteTask())
        self.edge("place", "route")
        self.node("bitstream", genfasm_bitstream.BitstreamTask())
        self.edge("route", "bitstream")


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
    def __init__(self, name: str = "fpgaflow-vpr-open-sta"):
        """
        Initializes the FPGAVPROpenSTAFlow.

        Args:
            name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("timing", timing.FPGATimingTask())
        self.edge("route", "timing")


##################################################
if __name__ == "__main__":
    for flow in [FPGANextPNRFlow(), FPGAVPRFlow(), FPGAXilinxFlow()]:
        flow.write_flowgraph(f"{flow.name}.png")
