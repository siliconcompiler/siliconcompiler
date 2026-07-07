#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Design, Project
from siliconcompiler.flows.formalflow import FormalFlow


def main():
    """
    Cover check of the SymbiYosys quickstart 'cover' design.

    Mirrors the official quickstart cover.sby: the solver searches for
    input sequences that drive a hash register to specific values,
    producing a reachability trace for every cover() statement.
    """
    design = Design("cover")
    design.set_dataroot("sby_quickstart", __file__)
    design.set_topmodule("top", fileset="rtl")
    design.add_file("cover.sv", dataroot="sby_quickstart", fileset="rtl")

    project = Project(design)
    project.add_fileset("rtl")
    project.set_flow(FormalFlow(mode="cover"))

    assert project.run(), "formal verification failed"

    project.summary()


if __name__ == "__main__":
    main()
