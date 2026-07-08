#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Design, Project
from siliconcompiler.flows.propertycheckflow import PropertyCheckFlow, PropertyCheckMode
from siliconcompiler.tools.sby.bmc import BMCTask


def main():
    """
    Bounded model check of the SymbiYosys quickstart 'demo' design.

    Mirrors the official quickstart demo.sby: a small counter whose
    'counter < 32' assertion is checked for 100 cycles.
    """
    design = Design("demo")
    design.set_dataroot("sva_sby", __file__)
    design.set_topmodule("demo", fileset="rtl")
    design.add_file("demo.sv", dataroot="sva_sby", fileset="rtl")

    project = Project(design)
    project.add_fileset("rtl")
    project.set_flow(PropertyCheckFlow(modes=PropertyCheckMode.BMC))

    # the official demo.sby checks 100 cycles
    BMCTask.find_task(project).set_sby_depth(100)

    project.run()

    project.summary()


if __name__ == "__main__":
    main()
