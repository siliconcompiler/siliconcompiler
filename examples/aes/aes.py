#!/usr/bin/env python3

# Import the core classes from the siliconcompiler library.
from siliconcompiler import ASICProject, Design
# Import a pre-defined "target" which sets up a specific PDK,
# standard cell library, and tool flow.
from siliconcompiler.targets import freepdk45_demo


def main():
    '''
    This script demonstrates a standard RTL-to-GDSII compilation flow
    for an AES (Advanced Encryption Standard) core. It takes Verilog source
    code and timing constraints as input and produces a final GDSII layout file.
    '''

    # --- Design Setup ---
    # The Design object is a blueprint that holds all the configuration
    # for a specific hardware design.
    design = Design("aes")

    # Set up a 'dataroot' to easily reference local files. `__file__` makes
    # the path relative to this Python script's location.
    design.set_dataroot("aes", __file__)

    # Configure the "rtl" (Register-Transfer Level) fileset.
    # A fileset is a named collection of files for a specific purpose.
    with design.active_dataroot("aes"), design.active_fileset("rtl"):
        # Specify the name of the top-level Verilog module.
        design.set_topmodule("aes")
        # Add the Verilog source file to this fileset.
        design.add_file("aes.v")

    # Configure the "sdc" (Synopsys Design Constraints) fileset.
    # This file contains timing information, such as the clock definition.
    with design.active_dataroot("aes"), design.active_fileset("sdc"):
        design.add_file("aes.sdc")

    # --- Project Setup ---
    # The ASICProject object links the design blueprint to a specific
    # technology target and compilation flow.
    project = ASICProject(design)

    # Tell the project which filesets to use for this compilation run.
    # Both the RTL source and the SDC constraints are needed.
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    # --- Target Loading ---
    # Load the target configuration. The `freepdk45_demo` target sets up the
    # project with all the necessary settings for the FreePDK45 technology,
    # including the process design kit (PDK), standard cell libraries,
    # and a default tool flow.
    project.load_target(freepdk45_demo.setup)

    # --- Execution ---
    # The run() command executes the entire pre-defined flow, which typically
    # includes steps like:
    # 1. Synthesis (converting Verilog to a netlist of standard cells)
    # 2. Floorplanning (defining the chip's overall shape and layout)
    # 3. Placement (placing the standard cells)
    # 4. Clock Tree Synthesis (building the clock distribution network)
    # 5. Routing (connecting the cells with metal wires)
    # 6. Finishing (DRC, LVS, GDS export)
    project.run()

    # --- Analysis ---
    # The summary() command prints a report of the key metrics from the run,
    # such as Worst Negative Slack (WNS) for timing, total cell area,
    # and power consumption estimates.
    project.summary()

    return project


# This is the standard entry point for a Python script.
if __name__ == '__main__':
    main()
