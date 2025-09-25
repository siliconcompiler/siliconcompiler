#!/usr/bin/env python3

# Import the core classes from the siliconcompiler library.
from siliconcompiler import ASICProject, Design
# Import a pre-defined target for the FreePDK45 process.
from siliconcompiler.targets import freepdk45_demo
# Import a specialized flow designed to handle Chisel source files.
from siliconcompiler.flows.asicflow import ChiselASICFlow


def main():
    """
    Builds the 'gcd' (Greatest Common Divisor) design using the FreePDK45 PDK.

    This script demonstrates a Chisel-to-GDSII flow. It sets up an ASIC
    project with a Chisel source file (.scala), loads the FreePDK45 target,
    runs a specialized compilation flow to handle the Chisel to Verilog
    conversion, and finally displays a summary and the final layout.
    """
    # --- Design Setup ---
    # Create a design object to hold the configuration.
    design = Design("gcd")

    # Set up a 'dataroot' to easily reference local files.
    design.set_dataroot("gcd", __file__)

    # Configure the "rtl" fileset. Note that the source file is Chisel (.scala).
    # The ChiselASICFlow will automatically convert this to Verilog.
    with design.active_dataroot("gcd"), design.active_fileset("rtl"):
        # The topmodule is the name of the Chisel 'class' to be compiled.
        design.set_topmodule("GCD")
        design.add_file("GCD.scala")

    # Configure the SDC (timing constraints) file.
    with design.active_dataroot("gcd"), design.active_fileset("sdc"):
        design.add_file("gcd.sdc")

    # --- Project Setup ---
    # Create an ASIC project from the design configuration.
    project = ASICProject(design)

    # Tell the project which filesets are needed for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the FreePDK45 demo process.
    freepdk45_demo(project)

    # Set the project to use the ChiselASICFlow. This pre-built flow
    # automatically inserts a Chisel-to-Verilog conversion step at the
    # beginning, before running the standard synthesis and PnR tools.
    project.set_flow(ChiselASICFlow())

    # --- Execution & Analysis ---
    # Execute the complete compilation flow.
    project.run()

    # Print a summary of the results (timing, area, power, etc.).
    project.summary()

    # Display the final physical layout in a GDS viewer (like KLayout).
    project.show()


if __name__ == '__main__':
    main()
