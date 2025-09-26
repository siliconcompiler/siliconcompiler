from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.openroad import init_floorplan
from siliconcompiler.tools.openroad import macro_placement
from siliconcompiler.tools.openroad import endcap_tapcell_insertion
from siliconcompiler.tools.openroad import power_grid
from siliconcompiler.tools.openroad import pin_placement
from siliconcompiler.tools.openroad import global_placement
from siliconcompiler.tools.openroad import repair_design
from siliconcompiler.tools.openroad import detailed_placement
from siliconcompiler.tools.openroad import clock_tree_synthesis
from siliconcompiler.tools.openroad import repair_timing
from siliconcompiler.tools.openroad import fillercell_insertion
from siliconcompiler.tools.openroad import global_route
from siliconcompiler.tools.openroad import antenna_repair
from siliconcompiler.tools.openroad import detailed_route
from siliconcompiler.tools.openroad import fillmetal_insertion
from siliconcompiler.tools.openroad import write_data
from siliconcompiler.tools.klayout import export as klayout_export

from siliconcompiler.tools.bambu.convert import ConvertTask
from siliconcompiler.tools.ghdl.convert import ConvertTask as GHDLConvertTask
from siliconcompiler.tools.sv2v.convert import ConvertTask as SV2VConvertTask
from siliconcompiler.tools.chisel.convert import ConvertTask as ChiselConvertTask

from siliconcompiler.tools.builtin import minimum

from siliconcompiler import Flowgraph
from siliconcompiler.tools.slang import elaborate


class ASICFlow(Flowgraph):
    '''A configurable ASIC compilation flow.

    This flow targets ASIC designs, taking RTL through a complete synthesis,
    place-and-route, and finishing flow.

    The flow is divided into the following major steps:

        * **elaborate**: RTL elaboration using Slang.
        * **synthesis**: RTL synthesis using Yosys.
        * **floorplan**: Floorplanning, including macro placement, tapcell/endcap
            insertion, power grid generation, and pin placement.
        * **place**: Global and detailed placement.
        * **cts**: Clock tree synthesis and post-CTS timing repair.
        * **route**: Global and detailed routing.
        * **dfm**: Design-for-manufacturing steps, primarily metal fill.
        * **write**: Writing out final views of the design (GDSII, etc.).

    The synthesis, floorplan, place, cts, and route steps support parallel
    execution to explore different strategies. This can be configured by
    setting the corresponding '_np' argument to a value greater than 1.

    Args:
        * syn_np (int): Number of parallel synthesis jobs to launch.
        * floorplan_np (int): Number of parallel floorplan jobs to launch.
        * place_np (int): Number of parallel placement jobs to launch.
        * cts_np (int): Number of parallel clock tree synthesis jobs to launch.
        * route_np (int): Number of parallel routing jobs to launch.
    '''

    def __init__(self, name: str = 'asicflow',
                 syn_np: int = 1,
                 floorplan_np: int = 1,
                 place_np: int = 1,
                 cts_np: int = 1,
                 route_np: int = 1):
        """Initializes the ASICFlow with configurable parallel execution.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch.
            * floorplan_np (int): The number of parallel floorplan jobs to launch.
            * place_np (int): The number of parallel placement jobs to launch.
            * cts_np (int): The number of parallel clock tree synthesis jobs to launch.
            * route_np (int): The number of parallel routing jobs to launch.
        """
        super().__init__()
        self.set_name(name)

        self.node("elaborate", elaborate.Elaborate())

        if syn_np > 1:
            syn_prev_node = "synthesis.min"
            self.node("synthesis.min", minimum.MinimumTask())
        else:
            syn_prev_node = "synthesis"

        for n in range(syn_np):
            self.node("synthesis", syn_asic.ASICSynthesis(), index=n)
            self.edge("elaborate", "synthesis", head_index=n)
            if syn_np > 1:
                self.edge("synthesis", "synthesis.min", tail_index=n)

        if floorplan_np > 1:
            fp_prev_node = "floorplan.min"
            self.node("floorplan.min", minimum.MinimumTask())
        else:
            fp_prev_node = "floorplan.pin_placement"

        for n in range(floorplan_np):
            self.node("floorplan.init", init_floorplan.InitFloorplanTask(), index=n)
            self.edge(syn_prev_node, "floorplan.init", head_index=n)
            self.node("floorplan.macro_placement", macro_placement.MacroPlacementTask(), index=n)
            self.edge("floorplan.init", "floorplan.macro_placement", tail_index=n, head_index=n)
            self.node("floorplan.tapcell", endcap_tapcell_insertion.EndCapTapCellTask(), index=n)
            self.edge("floorplan.macro_placement", "floorplan.tapcell", tail_index=n, head_index=n)
            self.node("floorplan.power_grid", power_grid.PowerGridTask(), index=n)
            self.edge("floorplan.tapcell", "floorplan.power_grid", tail_index=n, head_index=n)
            self.node("floorplan.pin_placement", pin_placement.PinPlacementTask(), index=n)
            self.edge("floorplan.power_grid", "floorplan.pin_placement", tail_index=n, head_index=n)
            if floorplan_np > 1:
                self.edge("floorplan.pin_placement", "floorplan.min", tail_index=n)

        if place_np > 1:
            place_prev_node = "place.min"
            self.node("place.min", minimum.MinimumTask())
        else:
            place_prev_node = "place.detailed"

        for n in range(place_np):
            self.node("place.global", global_placement.GlobalPlacementTask(), index=n)
            self.edge(fp_prev_node, "place.global", head_index=n)
            self.node("place.repair_design", repair_design.RepairDesignTask(), index=n)
            self.edge("place.global", "place.repair_design", tail_index=n, head_index=n)
            self.node("place.detailed", detailed_placement.DetailedPlacementTask(), index=n)
            self.edge("place.repair_design", "place.detailed", tail_index=n, head_index=n)
            if place_np > 1:
                self.edge("place.detailed", "place.min", tail_index=n)

        if cts_np > 1:
            cts_prev_node = "cts.min"
            self.node("cts.min", minimum.MinimumTask())
        else:
            cts_prev_node = "cts.fillcell"

        for n in range(cts_np):
            self.node("cts.clock_tree_synthesis", clock_tree_synthesis.CTSTask(), index=n)
            self.edge(place_prev_node, "cts.clock_tree_synthesis", head_index=n)
            self.node("cts.repair_timing", repair_timing.RepairTimingTask(), index=n)
            self.edge("cts.clock_tree_synthesis", "cts.repair_timing", tail_index=n, head_index=n)
            self.node("cts.fillcell", fillercell_insertion.FillCellTask(), index=n)
            self.edge("cts.repair_timing", "cts.fillcell", tail_index=n, head_index=n)
            if cts_np > 1:
                self.edge("cts.fillcell", "cts.min", tail_index=n)

        if route_np > 1:
            route_prev_node = "route.min"
            self.node("route.min", minimum.MinimumTask())
        else:
            route_prev_node = "route.detailed"

        for n in range(route_np):
            self.node("route.global", global_route.GlobalRouteTask(), index=n)
            self.edge(cts_prev_node, "route.global", head_index=n)
            self.node("route.antenna_repair", antenna_repair.AntennaRepairTask(), index=n)
            self.edge("route.global", "route.antenna_repair", tail_index=n, head_index=n)
            self.node("route.detailed", detailed_route.DetailedRouteTask(), index=n)
            self.edge("route.antenna_repair", "route.detailed", tail_index=n, head_index=n)
            if route_np > 1:
                self.edge("route.detailed", "route.min", tail_index=n)

        self.node("dfm.metal_fill", fillmetal_insertion.FillMetalTask())
        self.edge(route_prev_node, "dfm.metal_fill")

        self.node("write.views", write_data.WriteViewsTask())
        self.edge("dfm.metal_fill", "write.views")
        self.node("write.gds", klayout_export.ExportTask())
        self.edge("dfm.metal_fill", "write.gds")

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create a representative instance of the flow, typically with parallel
        execution features enabled to demonstrate the flow's capabilities.

        Returns:
            An instance of the ASICFlow class.
        '''
        return cls(syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)


class SV2VASICFlow(ASICFlow):
    '''A SystemVerilog-to-Verilog extension of the ASICFlow.

    This flow is intended for designs written in SystemVerilog that may not be
    fully supported by downstream synthesis or APR tools. It inserts a
    'convert' step using SV2V before the standard 'elaborate' step to ensure
    the design is in a compatible Verilog format.
    '''

    def __init__(self, name: str = 'sv2vasicflow',
                 syn_np: int = 1,
                 floorplan_np: int = 1,
                 place_np: int = 1,
                 cts_np: int = 1,
                 route_np: int = 1):
        """Initializes the SV2VASICFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch.
            * floorplan_np (int): The number of parallel floorplan jobs to launch.
            * place_np (int): The number of parallel placement jobs to launch.
            * cts_np (int): The number of parallel clock tree synthesis jobs to launch.
            * route_np (int): The number of parallel routing jobs to launch.
        """
        super().__init__(name,
                         syn_np=syn_np,
                         floorplan_np=floorplan_np,
                         place_np=place_np,
                         cts_np=cts_np,
                         route_np=route_np)

        self.insert_node("convert", SV2VConvertTask(), before_step="elaborate")


class HLSASICFlow(ASICFlow):
    '''A High-Level Synthesis (HLS) extension of the ASICFlow.

    This class inherits from ASICFlow and modifies it to support C-based HLS.
    It replaces the initial 'elaborate' step with a 'convert' step, which
    handles the conversion of HLS C code to RTL using the Bambu tool.
    '''

    def __init__(self, name: str = 'hlsasicflow',
                 syn_np: int = 1,
                 floorplan_np: int = 1,
                 place_np: int = 1,
                 cts_np: int = 1,
                 route_np: int = 1):
        """Initializes the HLSASICFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch.
            * floorplan_np (int): The number of parallel floorplan jobs to launch.
            * place_np (int): The number of parallel placement jobs to launch.
            * cts_np (int): The number of parallel clock tree synthesis jobs to launch.
            * route_np (int): The number of parallel routing jobs to launch.
        """
        super().__init__(name,
                         syn_np=syn_np,
                         floorplan_np=floorplan_np,
                         place_np=place_np,
                         cts_np=cts_np,
                         route_np=route_np)

        self.remove_node("elaborate")
        self.node("convert", ConvertTask())
        for n in range(syn_np):
            self.edge("convert", "synthesis", head_index=n)


class VHDLASICFlow(ASICFlow):
    '''A VHDL-based ASIC synthesis flow.

    This class extends the standard ASICFlow to support VHDL input by
    replacing the initial Verilog-focused 'elaborate' step with a 'convert'
    step. This new step uses GHDL to analyze and elaborate the VHDL design
    before synthesis.
    '''

    def __init__(self, name: str = 'vhdlasicflow',
                 syn_np: int = 1,
                 floorplan_np: int = 1,
                 place_np: int = 1,
                 cts_np: int = 1,
                 route_np: int = 1):
        '''Initializes the VHDL ASIC flow.

        This method sets up the flow graph for VHDL designs by:

            1. Removing the default 'elaborate' node.
            2. Adding a 'convert' node that runs the GHDLConvertTask.
            3. Connecting the new 'convert' node to the 'synthesis' node(s).

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch.
            * floorplan_np (int): The number of parallel floorplan jobs to launch.
            * place_np (int): The number of parallel placement jobs to launch.
            * cts_np (int): The number of parallel clock tree synthesis jobs to launch.
            * route_np (int): The number of parallel routing jobs to launch.
        '''
        super().__init__(name,
                         syn_np=syn_np,
                         floorplan_np=floorplan_np,
                         place_np=place_np,
                         cts_np=cts_np,
                         route_np=route_np)

        self.remove_node("elaborate")
        self.node("convert", GHDLConvertTask())
        for n in range(syn_np):
            self.edge("convert", "synthesis", head_index=n)


class ChiselASICFlow(ASICFlow):
    '''A Chisel-based ASIC synthesis flow.

    This class extends the standard ASICFlow to support designs written in
    the Chisel hardware construction language. It replaces the Verilog-focused
    'elaborate' step with a 'convert' step that uses the Chisel compiler to
    generate Verilog from the Chisel source before synthesis.
    '''

    def __init__(self, name: str = 'chiselasicflow',
                 syn_np: int = 1,
                 floorplan_np: int = 1,
                 place_np: int = 1,
                 cts_np: int = 1,
                 route_np: int = 1):
        """Initializes the ChiselASICFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch.
            * floorplan_np (int): The number of parallel floorplan jobs to launch.
            * place_np (int): The number of parallel placement jobs to launch.
            * cts_np (int): The number of parallel clock tree synthesis jobs to launch.
            * route_np (int): The number of parallel routing jobs to launch.
        """
        super().__init__(name,
                         syn_np=syn_np,
                         floorplan_np=floorplan_np,
                         place_np=place_np,
                         cts_np=cts_np,
                         route_np=route_np)
        self.remove_node("elaborate")
        self.node("convert", ChiselConvertTask())
        for n in range(syn_np):
            self.edge("convert", "synthesis", head_index=n)


##################################################
if __name__ == "__main__":
    flow = ASICFlow(syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)
    flow.write_flowgraph(f"{flow.name}.png")
