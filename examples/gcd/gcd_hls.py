#!/usr/bin/env python3
# Copyright 2020-2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import ASICProject, Design
from siliconcompiler.targets import freepdk45_demo
# Import a specialized flow designed to handle High-Level Synthesis.
from siliconcompiler.flows.asicflow import HLSASICFlow


def main():
    """
    Builds the 'gcd' design using the FreePDK45 PDK via a High-Level Synthesis (HLS) flow.

    This script demonstrates how to take a C source file (`gcd.c`) as the primary
    design input. It uses a specialized HLS flow to first synthesize the C code
    into Verilog RTL, and then runs that RTL through the standard GDSII compilation
    process.
    """
    # --- Design Setup ---
    # Create a design object to hold the configuration.
    design = Design("gcd")

    # Set up a 'dataroot' to easily reference local files.
    design.set_dataroot("gcd", __file__)

    # Configure the input fileset. While named "rtl", in an HLS flow,
    # the primary source is C/C++, not Verilog.
    with design.active_dataroot("gcd"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        # Add the C source file as the design input.
        design.add_file("gcd.c")

    # Configure the SDC (timing constraints) file for the HLS-generated module.
    with design.active_dataroot("gcd"), design.active_fileset("sdc"):
        design.add_file("gcd_hls.sdc")

    # --- Project Setup ---
    # Create an ASIC project from the design configuration.
    project = ASICProject(design)

    # Enable the necessary filesets for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the FreePDK45 demo process.
    freepdk45_demo.setup(project)

    # Set the project to use the HLSASICFlow. This is a pre-built flow
    # that automatically inserts an HLS step (using a tool like Bambu) at the
    # beginning to convert the C code to Verilog.
    project.set_flow(HLSASICFlow())

    # --- Execution & Analysis ---
    # Execute the complete HLS-to-GDSII compilation flow.
    project.run()

    # Print a summary of the results (timing, area, power, etc.).
    project.summary()

    # Display the final physical layout in a GDS viewer.
    project.show()


if __name__ == '__main__':
    main()
