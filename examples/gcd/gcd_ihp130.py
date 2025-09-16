#!/usr/bin/env python3
# Copyright 2024-2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import ASICProject, Design
# Import the target for the IHP 130nm open source PDK.
from siliconcompiler.targets import ihp130_demo
# Import the specialized flow for running only DRC.
from siliconcompiler.flows.drcflow import DRCFlow
# Import the KLayout DRC task to configure it.
from siliconcompiler.tools.klayout.drc import DRCTask


def main():
    """
    Demonstrates a two-stage process using the IHP 130nm PDK:
    1. A full RTL-to-GDSII compilation for the 'gcd' design.
    2. A standalone Design Rule Check (DRC) on the resulting GDSII layout.
    """

    # --- Part 1: RTL-to-GDSII Compilation ---

    # --- Design Setup ---
    # Create a design object to hold the configuration.
    design = Design("gcd")

    # Set up a 'dataroot' to easily reference local files.
    design.set_dataroot("gcd", __file__)

    # Configure the "rtl" (Verilog) fileset.
    with design.active_dataroot("gcd"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.v")

    # Configure the "sdc" (timing constraints) fileset.
    with design.active_dataroot("gcd"), design.active_fileset("sdc"):
        design.add_file("gcd.sdc")

    # --- Project Setup ---
    # Create an ASIC project from the design configuration.
    project = ASICProject(design)

    # Tell the project which filesets are needed for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the IHP 130nm demo process.
    # This configures the project with the correct PDK, standard cell libraries,
    # and the default RTL-to-GDSII tool flow.
    project.load_target(ihp130_demo.setup)

    # --- Execution & Analysis ---
    # Execute the complete ASIC compilation flow (synthesis, place, route, etc.).
    project.run()

    # Print a summary of the results (timing, area, power, etc.).
    project.summary()

    # --- Part 2: Standalone DRC Verification ---

    # After the first run, we find the path to the output GDSII file...
    # ...and add it to a new 'layout' fileset. This GDSII file will be the
    # *input* for our next step.
    with design.active_fileset("layout"):
        design.set_topmodule("gcd")
        design.add_file(project.find_result('gds', step='write.gds'))

    # Add the new 'layout' fileset to the project for the next run.
    # `clobber=True` ensures it overwrites any previous configuration.
    project.add_fileset("layout", clobber=True)

    # Explicitly switch the project's flow to `DRCFlow`, a pre-built flow
    # designed only for running DRC on a layout.
    project.set_flow(DRCFlow())

    # Configure the DRC task. We specify that it should use the 'minimal'
    # DRC ruleset, which is defined by the IHP 130nm target.
    project.get_task(filter=DRCTask).set("var", "drc_name", "minimal")

    # Set a new jobname for this run to keep the output directories separate.
    project.set("option", "jobname", "drc")

    # Execute the DRC-only flow.
    project.run()

    # Display the summary for the DRC run. This will report if any DRC
    # violations were found.
    project.summary()


if __name__ == '__main__':
    main()
