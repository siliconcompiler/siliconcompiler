#!/usr/bin/env python3
# Copyright 2020-2025 Silicon Compiler Authors. All Rights Reserved.

import sys

from siliconcompiler import Design, Project
from siliconcompiler.flows.formalflow import FormalFlow


def main(mode="bmc"):
    """
    Formally verifies the 'counter' design with SymbiYosys.

    This script sets up a design with RTL that carries SVA assertions
    (guarded by `ifdef FORMAL), wraps it in a project, and runs the
    FormalFlow, which drives yosys + sby + an SMT solver. Supported
    modes: bmc (default), prove, cover.

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

    # Create a project and select the formal verification flow.
    project = Project(design)
    project.add_fileset("rtl")
    project.set_flow(FormalFlow(mode=mode))

    # Execute the flow; raises on a failed proof.
    assert project.run(), "formal verification failed"

    project.summary()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bmc")
