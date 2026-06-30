from siliconcompiler import Flowgraph

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

from siliconcompiler.tools.builtin import minimum

from siliconcompiler.flows.synflow import SynthesisFlow, SV2VSynthesisFlow, HLSSynthesisFlow, \
    VHDLSynthesisFlow, ChiselSynthesisFlow


class _ASICFlowBase(Flowgraph):
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

    def _synthesis(self, np):
        raise NotImplementedError("Subclasses must implement the _synthesis method.")

    def __init__(self, name: str = 'asicflow',
                 syn_np: int = 1,
                 floorplan_np: int = 1,
                 place_np: int = 1,
                 cts_np: int = 1,
                 route_np: int = 1):
        """Initializes the ASICFlow with configurable parallel execution.

        Args:
            * name (str): The name of the flow.
            * floorplan_np (int): The number of parallel floorplan jobs to launch.
            * place_np (int): The number of parallel placement jobs to launch.
            * cts_np (int): The number of parallel clock tree synthesis jobs to launch.
            * route_np (int): The number of parallel routing jobs to launch.
        """
        super().__init__()
        self.set_name(name)

        synth = self._synthesis(np=syn_np)
        self.graph(synth)

        prev_node = synth.get_exit_nodes()
        prev_node = [node for node in prev_node if node[0] != "timing"]
        if len(prev_node) == 0:
            timing_node = synth.get_exit_nodes()[0]
            node = synth.get_graph_node(timing_node[0], timing_node[1])
            prev_node = node.get_input()
        if len(prev_node) != 1:
            raise ValueError("Synthesis flow must have exactly one exit synthesis node.")
        prev_node = prev_node[0][0]  # Get the node name from the tuple

        for prefix, graph in [
                ("floorplan", FloorplanningFlow(np=floorplan_np)),
                ("place", PlacementFlow(np=place_np)),
                ("cts", ClockTreeSynthesisFlow(np=cts_np)),
                ("route", RoutingFlow(np=route_np)),
                ("dfm", DFMFlow(np=1))]:
            self.graph(graph, name=prefix)
            for node in graph.get_entry_nodes():
                self.edge(prev_node, f"{prefix}.{node[0]}", head_index=node[1])

            prev_node = graph.get_exit_nodes()
            if len(prev_node) != 1:
                raise ValueError(f"{graph.name} must have exactly one exit node.")
            prev_node = f"{prefix}.{prev_node[0][0]}"  # Get the node name from the tuple

        self.node("write.views", write_data.WriteViewsTask())
        self.edge(prev_node, "write.views")
        self.node("write.gds", klayout_export.ExportTask())
        self.edge(prev_node, "write.gds")

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


class FloorplanningFlow(Flowgraph):
    '''A flow that performs only the floorplanning portion of the ASIC flow.

    This flow is useful for quickly checking that a design can be successfully
    floorplanned without running synthesis or timing analysis. It includes
    macro placement, tapcell/endcap insertion, power grid generation, and pin
    placement.
    '''

    def __init__(self, name: str = 'floorplanningflow', np: int = 1):
        """
        Initializes the FloorplanningFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        for n in range(np):
            self.node("init", init_floorplan.InitFloorplanTask(), index=n)
            self.node("macro_placement", macro_placement.MacroPlacementTask(), index=n)
            self.edge("init", "macro_placement", tail_index=n, head_index=n)
            self.node("tapcell", endcap_tapcell_insertion.EndCapTapCellTask(), index=n)
            self.edge("macro_placement", "tapcell", tail_index=n, head_index=n)
            self.node("power_grid", power_grid.PowerGridTask(), index=n)
            self.edge("tapcell", "power_grid", tail_index=n, head_index=n)
            self.node("pin_placement", pin_placement.PinPlacementTask(), index=n)
            self.edge("power_grid", "pin_placement", tail_index=n, head_index=n)

        if np > 1:
            self.node("min", minimum.MinimumTask())
            for n in range(np):
                self.edge("pin_placement", "min", tail_index=n)

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create a representative instance of the flow, typically with parallel
        execution features enabled to demonstrate the flow's capabilities.

        Returns:
            An instance of the FloorplanningFlow class.
        '''
        return cls(np=3)


class PlacementFlow(Flowgraph):
    '''A flow that performs only the placement portion of the ASIC flow.

    This flow is useful for quickly checking that a design can be successfully
    placed without running synthesis or timing analysis. It includes global
    placement, repair, and detailed placement.
    '''

    def __init__(self, name: str = 'placementflow', np: int = 1):
        """
        Initializes the PlacementFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        for n in range(np):
            self.node("global_place", global_placement.GlobalPlacementTask(), index=n)
            self.node("repair_design", repair_design.RepairDesignTask(), index=n)
            self.edge("global_place", "repair_design", tail_index=n, head_index=n)
            self.node("detailed", detailed_placement.DetailedPlacementTask(), index=n)
            self.edge("repair_design", "detailed", tail_index=n, head_index=n)

        if np > 1:
            self.node("min", minimum.MinimumTask())
            for n in range(np):
                self.edge("detailed", "min", tail_index=n)

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create a representative instance of the flow, typically with parallel
        execution features enabled to demonstrate the flow's capabilities.

        Returns:
            An instance of the PlacementFlow class.
        '''
        return cls(np=3)


class ClockTreeSynthesisFlow(Flowgraph):
    '''A flow that performs only the clock tree synthesis portion of the ASIC flow.

    This flow is useful for quickly checking that a design can be successfully
    clock tree synthesized without running synthesis or timing analysis. It
    includes clock tree synthesis, repair, and filler cell insertion.
    '''

    def __init__(self, name: str = 'ctssflow', np: int = 1):
        """
        Initializes the ClockTreeSynthesisFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        for n in range(np):
            self.node("clock_tree_synthesis", clock_tree_synthesis.CTSTask(), index=n)
            self.node("repair_timing", repair_timing.RepairTimingTask(), index=n)
            self.edge("clock_tree_synthesis", "repair_timing", tail_index=n, head_index=n)

        if np > 1:
            self.node("min", minimum.MinimumTask())
            for n in range(np):
                self.edge("repair_timing", "min", tail_index=n)

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create a representative instance of the flow, typically with parallel
        execution features enabled to demonstrate the flow's capabilities.

        Returns:
            An instance of the ClockTreeSynthesisFlow class.
        '''
        return cls(np=3)


class RoutingFlow(Flowgraph):
    '''A flow that performs only the routing portion of the ASIC flow.

    This flow is useful for quickly checking that a design can be successfully
    routed without running synthesis or timing analysis. It includes global
    routing, antenna repair, and detailed routing.
    '''

    def __init__(self, name: str = 'routingflow', np: int = 1):
        """
        Initializes the RoutingFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        for n in range(np):
            self.node("global_route", global_route.GlobalRouteTask(), index=n)
            self.node("antenna_repair", antenna_repair.AntennaRepairTask(), index=n)
            self.edge("global_route", "antenna_repair", tail_index=n, head_index=n)
            self.node("detailed", detailed_route.DetailedRouteTask(), index=n)
            self.edge("antenna_repair", "detailed", tail_index=n, head_index=n)

        if np > 1:
            self.node("min", minimum.MinimumTask())
            for n in range(np):
                self.edge("detailed", "min", tail_index=n)

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create a representative instance of the flow, typically with parallel
        execution features enabled to demonstrate the flow's capabilities.

        Returns:
            An instance of the DFMFlow class.
        '''
        return cls(np=3)


class DFMFlow(Flowgraph):
    '''A flow that performs only the design-for-manufacturing (DFM) portion of the ASIC flow.

    This flow is useful for quickly checking that a design can be successfully
    processed for DFM without running synthesis or timing analysis. It includes
    metal fill insertion.
    '''

    def __init__(self, name: str = 'dfmflow', np: int = 1):
        """
        Initializes the DFMFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        for n in range(np):
            self.node("fillcell", fillercell_insertion.FillCellTask(), index=n)
            self.node("metal_fill", fillmetal_insertion.FillMetalTask(), index=n)
            self.edge("fillcell", "metal_fill", tail_index=n, head_index=n)

        if np > 1:
            self.node("min", minimum.MinimumTask())
            for n in range(np):
                self.edge("metal_fill", "min", tail_index=n)

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create a representative instance of the flow, typically with parallel
        execution features enabled to demonstrate the flow's capabilities.

        Returns:
            An instance of the DFMFlow class.
        '''
        return cls(np=3)


class ASICFlow(_ASICFlowBase):
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

    def _synthesis(self, np):
        return SynthesisFlow(syn_np=np)


class SV2VASICFlow(ASICFlow):
    '''A SystemVerilog-to-Verilog extension of the ASICFlow.

    This flow is intended for designs written in SystemVerilog that may not be
    fully supported by downstream synthesis or APR tools. It inserts a
    'convert' step using SV2V before the standard 'elaborate' step to ensure
    the design is in a compatible Verilog format.
    '''

    def _synthesis(self, np):
        return SV2VSynthesisFlow(syn_np=np)

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


class HLSASICFlow(ASICFlow):
    '''A High-Level Synthesis (HLS) extension of the ASICFlow.

    This class inherits from ASICFlow and modifies it to support C-based HLS.
    It replaces the initial 'elaborate' step with a 'convert' step, which
    handles the conversion of HLS C code to RTL using the Bambu tool.
    '''

    def _synthesis(self, np):
        return HLSSynthesisFlow(syn_np=np)

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


class VHDLASICFlow(ASICFlow):
    '''A VHDL-based ASIC synthesis flow.

    This class extends the standard ASICFlow to support VHDL input by
    replacing the initial Verilog-focused 'elaborate' step with a 'convert'
    step. This new step uses GHDL to analyze and elaborate the VHDL design
    before synthesis.
    '''

    def _synthesis(self, np):
        return VHDLSynthesisFlow(syn_np=np)

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


class ChiselASICFlow(ASICFlow):
    '''A Chisel-based ASIC synthesis flow.

    This class extends the standard ASICFlow to support designs written in
    the Chisel hardware construction language. It replaces the Verilog-focused
    'elaborate' step with a 'convert' step that uses the Chisel compiler to
    generate Verilog from the Chisel source before synthesis.
    '''

    def _synthesis(self, np):
        return ChiselSynthesisFlow(syn_np=np)

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


##################################################
if __name__ == "__main__":
    for flowcls in [ASICFlow, SV2VASICFlow, HLSASICFlow, VHDLASICFlow, ChiselASICFlow]:
        flow = flowcls(syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)
        flow.write_flowgraph(f"{flow.name}.png")
