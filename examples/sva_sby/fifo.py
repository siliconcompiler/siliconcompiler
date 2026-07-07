#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Design, Project
from siliconcompiler.flows.formalflow import FormalFlow


def main():
    """
    Formally verifies the FIFO from the SymbiYosys tutorial.

    The design carries named assertions (address/count consistency,
    full/empty behavior) and cover statements, so the same RTL is
    driven through all three sby modes: bounded model check, unbounded
    proof by k-induction, and cover reachability.
    """
    for mode in ("bmc", "prove", "cover"):
        design = Design("fifo")
        design.set_dataroot("sva_sby", __file__)
        design.set_topmodule("fifo", fileset="rtl")
        design.add_file("fifo.sv", dataroot="sva_sby", fileset="rtl")

        project = Project(design)
        project.add_fileset("rtl")
        project.set_flow(FormalFlow(mode=mode))
        project.set("option", "jobname", f"job_{mode}")

        assert project.run(), f"formal verification failed in {mode} mode"

        project.summary()


if __name__ == "__main__":
    main()
