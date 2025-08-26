from siliconcompiler.tools.yosys import syn_fpga as yosys_syn
from siliconcompiler.tools.vpr import place as vpr_place
from siliconcompiler.tools.vpr import route as vpr_route
from siliconcompiler.tools.genfasm import bitstream as genfasm_bitstream

from siliconcompiler.tools.vivado import syn_fpga as vivado_syn
from siliconcompiler.tools.vivado import place as vivado_place
from siliconcompiler.tools.vivado import route as vivado_route
from siliconcompiler.tools.vivado import bitstream as vivado_bitstream

from siliconcompiler.tools.nextpnr import apr as nextpnr_apr


from siliconcompiler import FlowgraphSchema
from siliconcompiler.tools.slang import elaborate


class FPGAXilinxFlow(FlowgraphSchema):
    '''
    A configurable FPGA compilation flow.

    The 'fpgaflow' module is a configurable FPGA flow with support for
    open source and commercial tool flows.

    The following step convention is recommended for VPR.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **place**: FPGA specific placement step
    * **route**: FPGA specific routing step
    * **bitstream**: Bitstream generation

    Note that nextpnr does not appear to support breaking placement, routing,
    and bitstream generation into individual steps, leading to the following
    recommended step convention

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **apr**: One-step execution of place, route, bitstream with nextpnr

    Args:
        - fpgaflow_type (str): this parameter can be used to select a specific
          fpga flow instead of one selected from the partname.
        - partname (str): this parameter can be used to select a specific fpga
          flow instead of one selected from the partname set in the schema.
    '''
    def __init__(self, name: str = "fpgaflow-xilinx"):
        super().__init__(name)

        self.node("syn_fpga", vivado_syn.SynthesisTask())
        self.node("place", vivado_place.PlaceTask())
        self.edge("syn_fpga", "place")
        self.node("route", vivado_route.RouteTask())
        self.edge("place", "route")
        self.node("bitstream", vivado_bitstream.BitstreamTask())
        self.edge("route", "bitstream")


class FPGANextPNRFlow(FlowgraphSchema):
    '''
    A configurable FPGA compilation flow.

    The 'fpgaflow' module is a configurable FPGA flow with support for
    open source and commercial tool flows.

    The following step convention is recommended for VPR.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **place**: FPGA specific placement step
    * **route**: FPGA specific routing step
    * **bitstream**: Bitstream generation

    Note that nextpnr does not appear to support breaking placement, routing,
    and bitstream generation into individual steps, leading to the following
    recommended step convention

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **apr**: One-step execution of place, route, bitstream with nextpnr

    Args:
        - fpgaflow_type (str): this parameter can be used to select a specific
          fpga flow instead of one selected from the partname.
        - partname (str): this parameter can be used to select a specific fpga
          flow instead of one selected from the partname set in the schema.
    '''
    def __init__(self, name: str = "fpgaflow-nextpnr"):
        super().__init__(name)

        self.node("syn_fpga", yosys_syn.FPGASynthesis())
        self.node("apr", nextpnr_apr.APRTask())
        self.edge("syn_fpga", "apr")


class FPGAVPRFlow(FlowgraphSchema):
    '''
    A configurable FPGA compilation flow.

    The 'fpgaflow' module is a configurable FPGA flow with support for
    open source and commercial tool flows.

    The following step convention is recommended for VPR.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **place**: FPGA specific placement step
    * **route**: FPGA specific routing step
    * **bitstream**: Bitstream generation

    Note that nextpnr does not appear to support breaking placement, routing,
    and bitstream generation into individual steps, leading to the following
    recommended step convention

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **apr**: One-step execution of place, route, bitstream with nextpnr

    Args:
        - fpgaflow_type (str): this parameter can be used to select a specific
          fpga flow instead of one selected from the partname.
        - partname (str): this parameter can be used to select a specific fpga
          flow instead of one selected from the partname set in the schema.
    '''
    def __init__(self, name: str = "fpgaflow-vpr"):
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


##################################################
if __name__ == "__main__":
    for flow in [FPGANextPNRFlow(), FPGAVPRFlow(), FPGAXilinxFlow()]:
        flow.write_flowgraph(f"{flow.name}.png")
