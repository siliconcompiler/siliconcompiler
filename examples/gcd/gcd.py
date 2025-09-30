#!/usr/bin/env python3
# Copyright 2020-2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import ASIC, Design
from siliconcompiler.targets import freepdk45_demo


def main():
    """
    Builds the 'gcd' (Greatest Common Divisor) design using the FreePDK45 PDK.

    This script sets up a basic ASIC project, configures the design
    with its RTL and SDC files, loads the FreePDK45 demo target,
    runs the compilation flow, and displays a summary and the final layout.
    """
    # --- Design Setup ---
    # Create a design object to hold the configuration.
    design = Design("gcd")

    # Set up a 'dataroot' to easily reference local files. This makes it
    # convenient to specify file paths relative to this script's location.
    design.set_dataroot("gcd", __file__)

    # Configure the "rtl" (Register-Transfer Level) fileset.
    # A fileset is a collection of files for a specific purpose.
    with design.active_dataroot("gcd"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.v")

    # Configure the "sdc" (Synopsys Design Constraints) fileset.
    # This file contains timing constraints for the design.
    with design.active_dataroot("gcd"), design.active_fileset("sdc"):
        design.add_file("gcd.sdc")

    # --- Project Setup ---
    # Create an ASIC project from the design configuration.
    project = ASIC(design)

    # Tell the project which filesets are needed for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the FreePDK45 demo process.
    # This configures the project with the correct PDK, standard cell libraries,
    # and tool flow for this technology.
    freepdk45_demo(project)

    # --- Execution & Analysis ---
    # Execute the complete ASIC compilation flow (synthesis, place, route, etc.).
    project.run()

    # Print a summary of the results (timing, area, power, etc.).
    project.summary()

    # Display the final physical layout in a GDS viewer (like KLayout).
    project.show()


if __name__ == '__main__':
    main()
