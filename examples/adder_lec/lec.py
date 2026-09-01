#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import ASIC, Design, Flowgraph
from siliconcompiler.targets import freepdk45_demo

from siliconcompiler.flows.formalflow import SECFlow
from siliconcompiler.flows.synflow import SynthesisFlow


def main():
    """
    Checks the synthesized 'adder' netlist against the RTL it came from.

    This script sets up an ASIC project for a small adder, synthesizes it into a
    Nangate45 netlist, and checks that netlist against the RTL with
    Kepler-formal.

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

    # SECFlow holds only the equivalence check, so graft it onto a flow which
    # builds the two views it compares: the elaborated RTL and the netlist
    # synthesized from it. Timing analysis is not needed here, so leave it out.
    flow = Flowgraph("adder-sec")
    flow.graph(SynthesisFlow(timing_np=0))
    flow.graph(SECFlow())

    # Synthesis does not re-emit the RTL it consumed, so the check reads it
    # from elaboration.
    flow.edge("elaborate", "sec")
    flow.edge("synthesis", "sec")

    project.set_flow(flow)

    # Execute the flow.
    project.run()

    # Print a summary of the equivalence check results.
    project.summary()


if __name__ == '__main__':
    main()
