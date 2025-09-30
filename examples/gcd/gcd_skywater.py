#!/usr/bin/env python3

from siliconcompiler import ASIC, Design
# Import the target for the Skywater 130nm open source PDK.
from siliconcompiler.targets import skywater130_demo
# Import the specialized flow for running signoff checks (DRC and LVS).
from siliconcompiler.flows.signoffflow import SignoffFlow


def main():
    """
    Demonstrates a two-stage process using the Skywater 130nm PDK:
    1. A full RTL-to-GDSII compilation for the 'gcd' design.
    2. Standalone signoff (LVS and DRC) on the resulting GDSII layout.
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
    project = ASIC(design)

    # Tell the project which filesets are needed for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the Skywater 130nm demo process.
    # This configures the project with the correct PDK, standard cell libraries,
    # and the default RTL-to-GDSII tool flow.
    skywater130_demo(project)

    # Set a unique name for this job run.
    project.set("option", "jobname", "rtl2gds")

    # --- Execution & Analysis ---
    # Execute the complete ASIC compilation flow (synthesis, place, route, etc.).
    project.run()

    # Print a summary of the results (timing, area, power, etc.).
    project.summary()

    # --- Part 2: Standalone LVS and DRC Verification ---

    # After the first run, we find the paths to the output GDSII and netlist files...
    # ...and add them to a new 'layout' fileset. These files will be the
    # *inputs* for our next signoff step.
    with design.active_fileset("layout"):
        design.set_topmodule("gcd")
        design.add_file(project.find_result('gds', step='write.gds'))
        design.add_file(project.find_result('vg', step='write.views'))

    # Add the new 'layout' fileset to the project for the next run.
    # `clobber=True` ensures it overwrites the fileset if it already exists.
    project.add_fileset("layout", clobber=True)

    # Explicitly switch the project's flow to `SignoffFlow`, a pre-built flow
    # designed for running DRC and LVS checks on a layout.
    project.set_flow(SignoffFlow())

    # Set a unique name for this job run.
    project.set("option", "jobname", "signoff")

    # Execute the signoff flow.
    project.run()

    # Print a summary of the signoff results.
    project.summary()


if __name__ == '__main__':
    main()
