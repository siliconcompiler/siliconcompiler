#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import ASIC, Design
from siliconcompiler.targets import freepdk45_demo

from siliconcompiler.flows.formalflow import LECFlow


def main():
    """
    Checks the synthesized 'adder' netlist against the RTL it came from.

    This script sets up an ASIC project for a small adder and runs the
    LECFlow, which synthesizes the RTL into a Nangate45 netlist and then
    checks that netlist against the RTL with Kepler-formal.

    Requires: yosys, kepler-formal; freepdk45 (via lambdapdk)
    """
    # Create a design object to hold the configuration.
    design = Design("adder")

    # Set the root directory for the design's source files.
    design.set_dataroot("adder_lec", __file__)

    # Configure the RTL (Verilog) source files.
    design.set_topmodule("adder", fileset="rtl")
    design.add_file("adder.v", dataroot="adder_lec", fileset="rtl")

    # Create an ASIC project from the design configuration.
    project = ASIC(design)

    # Enable the necessary filesets for the compilation flow.
    project.add_fileset("rtl")

    # Load the pre-defined target for the FreePDK45 demo process.
    freepdk45_demo(project)

    # Specify the equivalence check flow, which replaces the target's.
    project.set_flow(LECFlow())

    # Execute the flow.
    project.run()

    # Print a summary of the equivalence check results.
    project.summary()


if __name__ == '__main__':
    main()
