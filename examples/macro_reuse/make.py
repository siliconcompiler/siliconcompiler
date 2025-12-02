#!/usr/bin/env python3

# # Instantiating a hardened module **A** twice in a module **B**
#
# Hardened modules allow predictable timing, efficient placement, and scalable
# hierarchical ASIC design.
#
# This tutorial demonstrates how to use siliconCompiler to harden a
# verilog module as a reusable macro, and then instantiate it multiple times in
# another module by:
#
# 1. Writing a simple verilog module **A**
#
# 2. Synthesizing, placing, and routing **A** using siliconCompiler
#
# 3. Packaging the resulting layout and timing models from **A** as a hard macro
#
# 4. Instantiating the hard macro **A** twice inside a second module **B**
#
# 5. Running the ASIC flow on module **B**
#
# All these steps are contained in the [python script](https://github.com/philiprbrenan/silicon_compiler_mod_A_in_mod_B/blob/main/silicon_compiler_mod_A_in_mod_B.py)  detailed below.
#
# To run this script from its containing folder:<br>
#
# ```bash
# docker run --rm -v "$(pwd):/sc_work" \
#   ghcr.io/siliconcompiler/sc_runner:v0.35.3 \
#   python3 silicon_compiler_mod_A_in_mod_B.py
# ```
#
# The image output will appear in: ``./build/B/job0/write.gds/0/outputs/B.png``
#
# ## Environment Setup
#
# Import the tools to be used:
#

from siliconcompiler import Design, ASIC, StdCellLibrary
from siliconcompiler.targets import skywater130_demo


class And(Design):
    def __init__(self):
        super().__init__("and")

        self.set_dataroot("local", __file__)

        self.set_topmodule("mod_and", fileset="rtl")
        self.add_file("and.v", fileset="rtl")


class Top(Design):
    def __init__(self):
        super().__init__("top")

        self.set_dataroot("local", __file__)

        self.set_topmodule("top", fileset="rtl")
        self.add_file("top.v", fileset="rtl")
        self.add_depfileset(And(), depfileset="rtl", fileset="rtl")


def build_and() -> StdCellLibrary:
    project = ASIC(And())
    project.add_fileset("rtl")
    skywater130_demo(project)

    project.run()
    project.summary()
    project.snapshot()

    library = StdCellLibrary("module_and")
    library.add_asic_pdk(project.get("asic", "pdk"))

    with library.active_fileset("models.physical"):
        library.add_file(project.find_result("lef", step="write.views"))
        library.add_file(project.find_result("gds", step="write.gds"))
        library.add_asic_aprfileset()

    for corner in ("slow", "typical", "fast"):
        with library.active_fileset(f"models.timing.{corner}"):
            library.add_file(project.find_result(f"{corner}.lib", step="write.views"))
            library.add_asic_libcornerfileset(corner, "nldm")

    return library


def build_top(size: int = 200, margin: int = 10):
    project = ASIC(Top())
    project.add_fileset('rtl')

    # Replace verilog RTL for and with harded module
    project.add_alias(And(), "rtl", None, None)
    project.add_asiclib(build_and())

    skywater130_demo(project)                                                   # Technology being used
    #
    # Setting core and die area correctly is crucial for successful macro placement.
    #
    project.constraint.area.set_diearea_rectangle(size, size, coremargin=margin)                   # Silicon area occupied by the design

    project.run()
    project.summary()
    project.snapshot()


if __name__ == "__main__":
    build_top()
