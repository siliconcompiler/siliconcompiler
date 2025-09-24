#!/usr/bin/env python3

# Import the core classes from the siliconcompiler library.
from siliconcompiler import ASICProject, Design
# Import a pre-defined target for the FreePDK45 process.
from siliconcompiler.targets import freepdk45_demo
# Import a specialized flow designed to handle VHDL source files.
from siliconcompiler.flows.asicflow import VHDLASICFlow
# Import the specific task for GHDL to configure it.
from siliconcompiler.tools.ghdl.convert import ConvertTask
from siliconcompiler.tools import get_task


def main():
    '''
    This script demonstrates a VHDL to GDSII flow.
    It shows how SiliconCompiler uses a specialized flow to automatically
    convert VHDL source code into Verilog before running the standard
    synthesis, place, and route steps.
    '''

    # --- Design Setup ---
    # Create a design schema to hold the project's configuration.
    design = Design("ghdl_fsynopsys")
    # Set up a 'dataroot' to easily reference local files.
    design.set_dataroot("ghdl_fsynopsys", __file__)

    # Configure the "rtl" fileset. Note that the source file is VHDL (.vhd).
    with design.active_dataroot("ghdl_fsynopsys"), design.active_fileset("rtl"):
        design.set_topmodule("binary_4_bit_adder_top")
        design.add_file("binary_4_bit_adder_top.vhd")

    # --- Project Setup ---
    # Create a standard ASIC project.
    project = ASICProject(design)

    # Tell the project to use the "rtl" fileset we defined.
    project.add_fileset("rtl")

    # Load the target configuration for the FreePDK45 technology.
    freepdk45_demo.setup(project)

    # --- Flow Configuration ---
    # Set the project to use the VHDLASICFlow. This is a pre-built flow
    # that automatically inserts a VHDL-to-Verilog conversion step at the
    # beginning, using the GHDL tool.
    project.set_flow(VHDLASICFlow())

    # --- Task-Specific Adjustments ---
    # Get the specific task that handles the VHDL conversion (ConvertTask).
    # We then set a tool-specific option on it. The `set_usefsynopsys(True)`
    # option tells GHDL to add a `use` clause for Synopsys libraries, which
    # helps ensure the generated Verilog is compatible with synthesis tools.
    get_task(project, filter=ConvertTask).set_usefsynopsys(True)

    # --- Execution & Analysis ---
    # Run the complete flow. SC will first run GHDL to convert the VHDL
    # file to Verilog, and then proceed with the rest of the ASIC flow.
    project.run()

    # Display a summary of the results (timing, area, etc.).
    project.summary()

    return project


if __name__ == '__main__':
    main()
