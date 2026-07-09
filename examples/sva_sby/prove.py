#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Design, Project
from siliconcompiler.flows.formalflow import PropertyCheckFlow, PropertyCheckMode


def main():
    """
    Unbounded proof of the SymbiYosys quickstart 'prove' design.

    Mirrors the official quickstart prove.sby: a testbench wraps the
    demo unit, assumes reset behavior, and its assertion is proven for
    all reachable states by k-induction.
    """
    design = Design("prove")
    design.set_dataroot("sva_sby", __file__)
    design.set_topmodule("testbench", fileset="rtl")
    design.add_file("prove.sv", dataroot="sva_sby", fileset="rtl")

    project = Project(design)
    project.add_fileset("rtl")
    project.set_flow(PropertyCheckFlow(modes=PropertyCheckMode.PROVE))

    project.run()

    project.summary()


if __name__ == "__main__":
    main()
