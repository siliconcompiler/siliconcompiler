#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
"""Uniquify parameterized modules for hardening.

A hardened macro has no parameters, so before hardening a parameterized module
we must discover which concrete parameter combinations it is instantiated with
across the design, generate a parameter-free variant for each (to harden), and a
parameterized wrapper that dispatches to them. This mirrors how lambdalib maps an
abstract cell onto hardened macros.

The whole lifecycle is driven by the :class:`Uniquified` helper on the
`heartbeat_top` design (which depends on the parameterized `heartbeat` and
`prescaler` modules):

1. construct -- enumerate + generate, and register the new filesets,
2. build     -- harden each variant into a macro (needs EDA tools),
3. wireup    -- alias the wrappers in and inject the macros into the parent.
"""

import os

from siliconcompiler import ASIC, Design
from siliconcompiler.tools.slang.utils.macro import Uniquified


# The parameterized modules to uniquify. Several at once is fine; each variant
# name is prefixed with its module.
TARGET_MODULES = ["heartbeat", "prescaler"]

_DATAROOT = "uniquify"
_LIBDIR = os.path.join(os.path.dirname(__file__), "build", "uniquify")


class Heartbeat(Design):
    """Parameterized `heartbeat` module (its own reusable design)."""
    def __init__(self):
        super().__init__("heartbeat")
        self.set_dataroot(_DATAROOT, __file__)
        with self.active_fileset("rtl"), self.active_dataroot(_DATAROOT):
            self.set_topmodule("heartbeat")
            self.add_file("heartbeat.v")


class Prescaler(Design):
    """Parameterized `prescaler` module (its own reusable design)."""
    def __init__(self):
        super().__init__("prescaler")
        self.set_dataroot(_DATAROOT, __file__)
        with self.active_fileset("rtl"), self.active_dataroot(_DATAROOT):
            self.set_topmodule("prescaler")
            self.add_file("prescaler.v")


class HeartbeatTop(Design):
    """Parent design instantiating the parameterized submodules."""
    def __init__(self):
        super().__init__("heartbeat_top")
        self.set_dataroot(_DATAROOT, __file__)
        with self.active_fileset("rtl"), self.active_dataroot(_DATAROOT):
            self.set_topmodule("heartbeat_top")
            # The parent depends on the submodule RTL so it elaborates.
            self.add_file("heartbeat_top.v")
            self.add_depfileset(Heartbeat(), depfileset="rtl", fileset="rtl")
            self.add_depfileset(Prescaler(), depfileset="rtl", fileset="rtl")


def uniquify(libdir=_LIBDIR):
    """Set up uniquification of the target modules on a fresh parent design.

    Returns the :class:`Uniquified` handle: the wrapper/variant filesets are
    registered on the design, but nothing is hardened yet.
    """
    return Uniquified(HeartbeatTop(), TARGET_MODULES, libdir=libdir)


def _configure_freepdk45(project):
    """Configure a variant/parent ASIC run for FreePDK45."""
    from siliconcompiler.targets import freepdk45_demo
    from siliconcompiler.tools.openroad._apr import OpenROADPSMParameter

    freepdk45_demo(project)
    project.constraint.area.set_density(5.0)
    # The demo PDK has no power grid; skip IR-drop analysis.
    for task in OpenROADPSMParameter.find_task(project):
        task.set_openroad_psmenable(False)


def harden(libdir=_LIBDIR):
    """Full flow: harden every variant and build the parent with the macros.

    Requires EDA tools (yosys/OpenROAD).
    """
    uq = uniquify(libdir)
    uq.build(target=_configure_freepdk45, parallel=True)

    project = ASIC(uq.design)
    project.add_fileset("rtl")
    _configure_freepdk45(project)
    uq.wireup(project)

    project.run()
    project.summary()


def main():
    uq = uniquify()

    for module, variants in uq.variants.items():
        print(f"'{module}' -> {len(variants)} variant(s): {variants}")
    print()
    print("wrapper filesets:  ", uq.wrapper_filesets)
    print("hardened filesets: ", uq.hardened_filesets)

    # Materialize the generated sources (construction is disk-side-effect free),
    # then show one wrapper: it keeps the module name + parameters and dispatches
    # to the hardened variants.
    uq.write()
    with open(os.path.join(uq.outdir, "heartbeat.wrapper.v")) as fobj:
        print("\n" + "=" * 64 + "\nGenerated wrapper for 'heartbeat':\n")
        print(fobj.read())


if __name__ == "__main__":
    main()
