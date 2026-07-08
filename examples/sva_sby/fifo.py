#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Design, Project
from siliconcompiler.flows.propertycheckflow import PropertyCheckFlow, PropertyCheckMode


def main():
    """
    Formally verifies the FIFO from the SymbiYosys tutorial.

    The design carries named assertions (address/count consistency,
    full/empty behavior) and cover statements, so it is checked with all
    three modes at once - bounded model check, unbounded proof by
    k-induction, and cover reachability - each running as its own parallel
    node in a single job.
    """
    design = Design("fifo")
    design.set_dataroot("sva_sby", __file__)
    design.set_topmodule("fifo", fileset="rtl")
    design.add_file("fifo.sv", dataroot="sva_sby", fileset="rtl")

    project = Project(design)
    project.add_fileset("rtl")
    project.set_flow(PropertyCheckFlow(
        modes=PropertyCheckMode.BMC | PropertyCheckMode.PROVE | PropertyCheckMode.COVER))

    project.run()

    project.summary()


if __name__ == "__main__":
    main()
