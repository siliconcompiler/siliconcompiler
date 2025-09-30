#!/usr/bin/env python3
# Copyright 2020-2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import ASIC, Design
from siliconcompiler.targets import skywater130_demo


def main():
    """
    Builds the 'heartbeat' design using the skywater130 PDK.

    This script sets up a basic ASIC project, configures the design
    with its RTL and SDC files, loads the Skywater130 demo target,
    runs the compilation flow, and displays a summary and the final layout.
    """
    # Create a design object to hold the configuration.
    design = Design("heartbeat")

    # Set the root directory for the design's source files.
    design.set_dataroot("heartbeat", __file__)

    # Configure the RTL (Verilog) source files.
    design.set_topmodule("heartbeat", fileset="rtl")
    design.add_file("heartbeat.v", dataroot="heartbeat", fileset="rtl")

    # Configure the SDC (timing constraints) file.
    design.add_file("heartbeat.sdc", dataroot="heartbeat", fileset="sdc")

    # Create an ASIC project from the design configuration.
    project = ASIC(design)

    # Enable the necessary filesets for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the Skywater130 demo process.
    skywater130_demo(project)

    # Execute the compilation flow.
    project.run()

    # Print a summary of the results (timing, area, power, etc.).
    project.summary()

    # Display the final physical layout in a GDS viewer.
    project.show()


if __name__ == '__main__':
    main()
