#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Design, Project
from siliconcompiler.flows.formalflow import PropertyCheckFlow, PropertyCheckMode


def main(modes=PropertyCheckMode.BMC):
    """
    Formally verifies the 'counter' design with SymbiYosys.

    This script sets up a design with RTL that carries SVA assertions
    (guarded by `ifdef FORMAL), wraps it in a project, and runs the
    PropertyCheckFlow, which drives yosys + sby + an SMT solver. Each
    selected PropertyCheckMode (bmc/prove/cover) runs as its own parallel
    node.

    The sby, yosys, and solver executables are located through the
    environment (PATH), so activate the desired formal toolchain before
    running.
    """
    # Create a design object to hold the configuration.
    design = Design("counter")

    # Set the root directory for the design's source files.
    design.set_dataroot("sva_sby", __file__)

    # Configure the RTL (Verilog) source files.
    design.set_topmodule("counter", fileset="rtl")
    design.add_file("counter.v", dataroot="sva_sby", fileset="rtl")

    # Create a project and select the property-checking flow.
    project = Project(design)
    project.add_fileset("rtl")
    project.set_flow(PropertyCheckFlow(modes=modes))

    # Execute the flow; raises on a failed proof.
    project.run()

    project.summary()


if __name__ == "__main__":
    main()
