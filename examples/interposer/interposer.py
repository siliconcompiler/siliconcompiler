#!/usr/bin/env python3
# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import ASICProject, Design, Flowgraph
# Import a specialized target for interposer designs. This target is configured
# with a technology setup (like layer stack) suitable for routing on an
# interposer, which typically lacks standard cells.
from siliconcompiler.targets import interposer_demo
# Import specific task definitions to allow for direct configuration.
from siliconcompiler.tools.openroad.rdlroute import RDLRouteTask
from siliconcompiler.tools.klayout.drc import DRCTask
from siliconcompiler.tools import get_task


def main():
    '''
    A simple example demonstrating how to build a silicon interposer flow.

    An interposer is a silicon die that acts as a bridge, providing
    connections between other dies (chiplets) and a package substrate. This
    design flow focuses on the physical routing of these connections (Redistribution
    Layers or RDL) rather than logic synthesis.
    '''

    # --- Design Setup ---
    # Create a design schema for the interposer.
    design = Design("interposer")
    # Set up a 'dataroot' for local files, relative to this script's location.
    design.set_dataroot("interposer", __file__)
    # The input is a Verilog netlist that defines the connectivity of the interposer.
    # It specifies which bumps (inputs) connect to which other bumps (outputs).
    with design.active_dataroot("interposer"), design.active_fileset("netlist"):
        design.set_topmodule("interposer")
        design.add_file("interposer.v")

    # --- Project Setup ---
    # Create a project, linking the design to a flow and target.
    project = ASICProject(design)

    # Add the netlist fileset to the project for this run.
    project.add_fileset("netlist")

    # Load the specialized interposer target.
    interposer_demo.setup(project)

    # --- Physical Constraints ---
    # Explicitly define the physical dimensions of the interposer die.
    # This is a critical piece of information for the routing tool.
    # The dimensions are specified in microns (width, height).
    project.get_areaconstituents().set_diearea_rectangle(1000, 500)

    # --- Custom Flowgraph Creation ---
    # We will build a custom flow by combining two pre-defined flows.
    # 'Flowgraph' allows for programmatic creation of flows.
    flow = Flowgraph("compositeflow")

    # 1. Import the entire 'interposerflow' from the target. This flow handles
    #    floorplanning and routing the redistribution layers (RDL).
    flow.graph(project.get("flowgraph", "interposerflow", field="schema"))
    # 2. Import the entire 'drcflow' from the target. This flow runs
    #    Design Rule Checking (DRC) to verify the final layout.
    flow.graph(project.get("flowgraph", "drcflow", field="schema"))
    # 3. Create a new edge to connect the two flows. We direct the output of the
    #    'write_gds' step (the end of interposerflow) to the input of the
    #    'drc' step (the start of drcflow).
    flow.edge("write_gds", "drc")

    # Set the project's flow to our newly created composite flow.
    project.set_flow(flow)

    # --- Task-Specific Configuration ---
    # Now we configure individual tasks (tools) within our custom flow.

    # 1. Configure the RDL Router (OpenROAD).
    # Get the specific task object for RDL routing from the project's flow.
    route: RDLRouteTask = get_task(project, filter=RDLRouteTask)
    # Set a dataroot for task-specific files.
    route.set_dataroot("interposer", __file__)
    with route.active_dataroot("interposer"):
        # Provide a Tcl script with commands for the router. This script is crucial
        # as it typically defines the locations and properties of the C4 bumps/pads
        # that the router needs to connect.
        route.add_openroad_rdlroute("bumps.tcl")

    # 2. Configure the DRC tool (KLayout).
    # Get the DRC task object and set a variable to specify which DRC deck to use.
    get_task(project, filter=DRCTask).set("var", "drc_name", "drc")

    # --- Execution & Analysis ---
    # Run the entire composite flow.
    project.run()

    # Display a summary of the results.
    project.summary()

    return project


if __name__ == '__main__':
    main()
