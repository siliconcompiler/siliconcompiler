from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.openroad import synth_cleanup
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

from siliconcompiler.flows.synflow import SynthesisFlow


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
    setting the corresponding ``*_np`` argument to a value greater than 1.

    Args:
        * name (str, optional): The name of the flow. If not provided, it
          defaults to 'asicflow-<language>'.
        * language (str): The hardware description language of the design. One
          of 'verilog', 'systemverilog', 'systemverilog-sv2v', 'chisel',
          'vhdl', or 'hls'.
        * syn_np (int): Number of parallel synthesis jobs to launch.
        * floorplan_np (int): Number of parallel floorplan jobs to launch.
        * place_np (int): Number of parallel placement jobs to launch.
        * cts_np (int): Number of parallel clock tree synthesis jobs to launch.
        * route_np (int): Number of parallel routing jobs to launch.
    '''

    def __init__(self, name: Optional[str] = None,
                 language: str = "verilog",
                 syn_np: int = 1,
                 floorplan_np: int = 1,
                 place_np: int = 1,
                 cts_np: int = 1,
                 route_np: int = 1):
        """Initializes the ASICFlow with configurable parallel execution.

        Args:
            * name (str): The name of the flow.
            * language (str): The hardware description language of the design.
            * syn_np (int): The number of parallel synthesis jobs to launch.
            * floorplan_np (int): The number of parallel floorplan jobs to launch.
            * place_np (int): The number of parallel placement jobs to launch.
            * cts_np (int): The number of parallel clock tree synthesis jobs to launch.
            * route_np (int): The number of parallel routing jobs to launch.
        """
        if name is None:
            name = f"asicflow-{language}"
        super().__init__(name)

        synth = SynthesisFlow(language=language, syn_np=syn_np)
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

        if prev_node == "min":
            self.rename_node("min", "synthesis.min")
            prev_node = "synthesis.min"
        self.rename_node("timing", "synthesis.timing")

        for prefix, graph in [
                ("cleanup", CleanupSynthFlow(np=1)),
                ("floorplan", FloorplanningFlow(np=floorplan_np)),
                ("place", PlacementFlow(np=place_np)),
                ("cts", ClockTreeSynthesisFlow(np=cts_np)),
                ("cts", FillerCellFlow(np=1)),  # use cts for now
                ("route", RoutingFlow(np=route_np)),
                ("dfm", MetalFillFlow(np=1))]:
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
        create representative instances of the flow, one for each supported
        source language, with parallel execution enabled to demonstrate the
        flow's capabilities.

        Returns:
            A list of ASICFlow instances, one per supported source language.
        '''
        return [
            cls(language="verilog",
                syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3),
            cls(language="systemverilog-sv2v",
                syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3),
            cls(language="chisel", syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3),
            cls(language="vhdl", syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3),
            cls(language="hls", syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3),
            cls(language="bluespec", syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)
        ]


class CleanupSynthFlow(Flowgraph):
    '''A flow that performs only the synthesis cleanup portion of the ASIC flow.

    This flow is useful for quickly checking that a design can be successfully
    cleaned up after synthesis without running floorplanning or timing analysis.
    It includes the removal of synthesis buffers and dead logic.
    '''

    def __init__(self, name: str = 'cleanup_synthflow', np: int = 1):
        """
        Initializes the CleanupSynthFlow.

        Args:
            * name (str): The name of the flow.
            * np (int): The number of parallel jobs to launch.
        """
        super().__init__(name)

        for n in range(np):
            self.node("clean", synth_cleanup.CleanupSynthTask(), index=n)

        if np > 1:
            self.node("min", minimum.MinimumTask())
            for n in range(np):
                self.edge("clean", "min", tail_index=n)

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create a representative instance of the flow, typically with parallel
        execution features enabled to demonstrate the flow's capabilities.

        Returns:
            An instance of the CleanupSynthFlow class.
        '''
        return cls(np=3)


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
            * np (int): The number of parallel jobs to launch.
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
            * np (int): The number of parallel jobs to launch.
        """
        super().__init__(name)

        for n in range(np):
            self.node("global", global_placement.GlobalPlacementTask(), index=n)
            self.node("repair_design", repair_design.RepairDesignTask(), index=n)
            self.edge("global", "repair_design", tail_index=n, head_index=n)
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
            * np (int): The number of parallel jobs to launch.
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
            * np (int): The number of parallel jobs to launch.
        """
        super().__init__(name)

        for n in range(np):
            self.node("global", global_route.GlobalRouteTask(), index=n)
            self.node("antenna_repair", antenna_repair.AntennaRepairTask(), index=n)
            self.edge("global", "antenna_repair", tail_index=n, head_index=n)
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
            An instance of the RoutingFlow class.
        '''
        return cls(np=3)


class MetalFillFlow(Flowgraph):
    '''A flow that performs only the metal fill portion of the ASIC flow.

    This flow is useful for quickly checking that a design can be successfully
    processed for metal fill without running synthesis or timing analysis. It includes
    metal fill insertion.
    '''

    def __init__(self, name: str = 'metalfillflow', np: int = 1):
        """
        Initializes the MetalFillFlow.

        Args:
            * name (str): The name of the flow.
            * np (int): The number of parallel jobs to launch.
        """
        super().__init__(name)

        for n in range(np):
            self.node("metal_fill", fillmetal_insertion.FillMetalTask(), index=n)

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
            An instance of the MetalFillFlow class.
        '''
        return cls(np=3)


class FillerCellFlow(Flowgraph):
    '''A flow that performs only the design-for-manufacturing (DFM) portion of the ASIC flow.

    This flow is useful for quickly checking that a design can be successfully
    processed for DFM without running synthesis or timing analysis. It includes
    filler cell insertion.
    '''

    def __init__(self, name: str = 'fillercellflow', np: int = 1):
        """
        Initializes the FillerCellFlow.

        Args:
            * name (str): The name of the flow.
            * np (int): The number of parallel jobs to launch.
        """
        super().__init__(name)

        for n in range(np):
            self.node("fillcell", fillercell_insertion.FillCellTask(), index=n)

        if np > 1:
            self.node("min", minimum.MinimumTask())
            for n in range(np):
                self.edge("fillcell", "min", tail_index=n)

    @classmethod
    def make_docs(cls):
        '''Creates an instance of the flow for documentation generation.

        This method is intended to be used by documentation generation tools to
        create a representative instance of the flow, typically with parallel
        execution features enabled to demonstrate the flow's capabilities.

        Returns:
            An instance of the FillerCellFlow class.
        '''
        return cls(np=3)


class SV2VASICFlow(ASICFlow):
    '''A SystemVerilog-to-Verilog variant of the ASIC compilation flow.

    This flow is intended for designs written in SystemVerilog that may not be
    fully supported by downstream synthesis or APR tools. The design is
    converted to a compatible Verilog format with SV2V during elaboration,
    before running the standard synthesis, place-and-route, and finishing steps.
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
                         language="systemverilog-sv2v",
                         syn_np=syn_np,
                         floorplan_np=floorplan_np,
                         place_np=place_np,
                         cts_np=cts_np,
                         route_np=route_np)

    @classmethod
    def make_docs(cls):
        return cls(syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)


class HLSASICFlow(ASICFlow):
    '''A High-Level Synthesis (HLS) variant of the ASIC compilation flow.

    This flow supports C-based HLS designs. The HLS C code is converted to RTL
    with the Bambu tool during elaboration, before running the standard
    synthesis, place-and-route, and finishing steps.
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
                         language="hls",
                         syn_np=syn_np,
                         floorplan_np=floorplan_np,
                         place_np=place_np,
                         cts_np=cts_np,
                         route_np=route_np)

    @classmethod
    def make_docs(cls):
        return cls(syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)


class VHDLASICFlow(ASICFlow):
    '''A VHDL variant of the ASIC compilation flow.

    This flow supports VHDL input. The design is analyzed and elaborated with
    GHDL during elaboration, before running the standard synthesis,
    place-and-route, and finishing steps.
    '''

    def __init__(self, name: str = 'vhdlasicflow',
                 syn_np: int = 1,
                 floorplan_np: int = 1,
                 place_np: int = 1,
                 cts_np: int = 1,
                 route_np: int = 1):
        '''Initializes the VHDLASICFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch.
            * floorplan_np (int): The number of parallel floorplan jobs to launch.
            * place_np (int): The number of parallel placement jobs to launch.
            * cts_np (int): The number of parallel clock tree synthesis jobs to launch.
            * route_np (int): The number of parallel routing jobs to launch.
        '''
        super().__init__(name,
                         language="vhdl",
                         syn_np=syn_np,
                         floorplan_np=floorplan_np,
                         place_np=place_np,
                         cts_np=cts_np,
                         route_np=route_np)

    @classmethod
    def make_docs(cls):
        return cls(syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)


class ChiselASICFlow(ASICFlow):
    '''A Chisel variant of the ASIC compilation flow.

    This flow supports designs written in the Chisel hardware construction
    language. The Chisel source is converted to Verilog with the Chisel compiler
    during elaboration, before running the standard synthesis, place-and-route,
    and finishing steps.
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
                         language="chisel",
                         syn_np=syn_np,
                         floorplan_np=floorplan_np,
                         place_np=place_np,
                         cts_np=cts_np,
                         route_np=route_np)

    @classmethod
    def make_docs(cls):
        return cls(syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)


##################################################
if __name__ == "__main__":
    for flowcls in [ASICFlow, SV2VASICFlow, HLSASICFlow, VHDLASICFlow, ChiselASICFlow]:
        flow = flowcls(syn_np=3, floorplan_np=3, place_np=3, cts_np=3, route_np=3)
        flow.write_flowgraph(f"{flow.name}.png", background="white")
