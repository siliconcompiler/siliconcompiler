#!/usr/bin/env python3
"""
Design Reuse of a Hardened Macro.

This script demonstrates a hierarchical ASIC design flow using SiliconCompiler.
It performs the following steps:
1. Defines a child module 'And'.
2. Hardens 'And' into a macro (Synthesize -> Place -> Route -> GDS/LEF/LIB).
3. Packages the results of 'And' into a reuseable StdCellLibrary object.
4. Defines a top-level module 'Top' that instantiates 'And' three times.
5. Builds 'Top' using the hardened 'And' macro.

Usage:
    docker run --rm -v "$(pwd):/sc_work" \
      ghcr.io/siliconcompiler/sc_runner:latest \
      python3 make.py
"""

from siliconcompiler import Design, ASIC, StdCellLibrary
from siliconcompiler.targets import skywater130_demo


class And(Design):
    """
    Defines the child module (an AND gate).
    Inheriting from Design allows us to encapsulate file paths and module names.
    """
    def __init__(self):
        super().__init__("and")
        # Set the root directory for relative paths to this file's location
        self.set_dataroot("local", __file__)
        self.set_topmodule("mod_and", fileset="rtl")
        self.add_file("and.v", fileset="rtl")


class Top(Design):
    """
    Defines the parent module (Top) which contains instances of the And gate.
    """
    def __init__(self):
        super().__init__("top")
        self.set_dataroot("local", __file__)
        self.set_topmodule("top", fileset="rtl")
        self.add_file("top.v", fileset="rtl")

        # Logically link 'And' so the linter/elaborator knows definitions exist.
        # Note: In the build_top() function, we will override this for physical implementation.
        self.add_depfileset(And(), depfileset="rtl", fileset="rtl")


def build_and() -> StdCellLibrary:
    """
    Hardens module 'And' and packages it as a library.

    Returns:
        StdCellLibrary: An object containing paths to the generated LEF, GDS, and LIB files.
    """

    project = ASIC(And())
    project.add_fileset("rtl")
    skywater130_demo(project)

    # Run the standard ASIC flow (Syn -> Floorplan -> Place -> Route -> Export)
    project.run()
    project.summary()

    # Create a reproducible snapshot of the build
    project.snapshot()

    # --- Packaging the Macro ---
    # Create a new library object to represent this hardened block
    library = StdCellLibrary("module_and")

    # Copy PDK name from the build project
    library.add_asic_pdk(project.get("asic", "pdk"))

    # Register Physical Views (GDS and Abstract)
    with library.active_fileset("models.physical"):
        # LEF: Abstract view for placement and routing in the parent
        library.add_file(project.find_result("lef", step="write.views"))
        # GDS: Actual layout for final merge
        library.add_file(project.find_result("gds", step="write.gds"))
        # Include necessary setup files for APR tools (like OpenROAD)
        library.add_asic_aprfileset()

    # Register Timing Views (Liberty files) for all available corners
    # This ensures the parent flow can perform timing analysis on the macro
    for corner in ("slow", "typical", "fast"):
        with library.active_fileset(f"models.timing.{corner}"):
            library.add_file(project.find_result(f"{corner}.lib", step="write.views"))
            library.add_asic_libcornerfileset(corner, "nldm")

    return library


def build_top(size: int = 250, margin: int = 10):
    """
    Builds the top-level module using the pre-built 'And' library.
    """

    project = ASIC(Top())
    project.add_fileset('rtl')

    # --- Hierarchical Configuration ---
    # 1. 'add_alias': Tells the tool "When you see module 'And', do not compile its RTL."
    #    This effectively turns 'And' into a blackbox during synthesis.
    project.add_alias(And(), "rtl", None, None)

    # 2. 'add_asiclib': Injects the pre-built library (LEF/LIB) we created in build_and().
    #    The APR tool will use the LEF for placement and the LIB for timing.
    project.add_asiclib(build_and())

    # Load target technology
    skywater130_demo(project)

    # --- Constraints ---
    # Setting explicit die area is critical for macros.
    # If the core is too small, the placer may fail to fit the child macros.
    project.constraint.area.set_diearea_rectangle(size, size, coremargin=margin)

    project.run()
    project.summary()
    project.snapshot()


def build_flat():
    """
    Reference build: Compiles Top and And together as one flat netlist.
    Useful for comparing results against the hierarchical flow.
    """

    project = ASIC(Top())
    project.add_fileset('rtl')
    skywater130_demo(project)

    project.run()
    project.summary()
    project.snapshot()


if __name__ == "__main__":
    # Execute the hierarchical flow
    build_top()
