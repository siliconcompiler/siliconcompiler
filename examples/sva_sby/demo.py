#!/usr/bin/env python3
# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
"""Formal property checking with SymbiYosys.

Five scripts covering the available ``PropertyCheckFlow`` modes -- singly, in
combination, and selectable. Run any of them directly:

* ``demo.py`` -- bounded model check: is the assertion true for 100 cycles?
* ``prove.py`` -- unbounded proof by k-induction: is it true for *all*
  reachable states?
* ``cover.py`` -- cover: is a stated condition reachable at all?
* ``fifo.py`` -- all three modes at once, against a FIFO carrying named
  assertions.
* ``counter_formal.py`` -- the same on a counter, with the mode as an argument.

The first three mirror the official SymbiYosys quickstart, so they are directly
comparable with its ``.sby`` files.

Requires: sby, yosys, and an SMT solver -- bitwuzla by default (boolector is
the other supported choice; see the ``engine`` parameter).
"""

from siliconcompiler import Design, Sim
from siliconcompiler.flows.formalflow import PropertyCheckFlow, PropertyCheckMode
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

    project = Sim(design)
    project.add_fileset("rtl")
    project.set_flow(PropertyCheckFlow(modes=PropertyCheckMode.BMC))

    # the official demo.sby checks 100 cycles
    BMCTask.find_task(project).set_sby_depth(100)

    project.run()

    project.summary()


if __name__ == "__main__":
    main()
