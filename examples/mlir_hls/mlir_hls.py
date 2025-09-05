#!/usr/bin/env python3

# Import necessary classes from the siliconcompiler library.
from siliconcompiler import ASICProject, DesignSchema
# Import a pre-defined target, which sets up the PDK, libraries, and toolchain.
from siliconcompiler.targets import freepdk45_demo
# Import the specialized High-Level Synthesis (HLS) flow.
from siliconcompiler.flows.asicflow import HLSASICFlow


def main():
    # --- Design Setup ---
    # A DesignSchema encapsulates all the source files, parameters, and
    # settings for a specific hardware design.
    design = DesignSchema("mlir")

    # Set up a 'dataroot' for local files. `__file__` makes the path
    # relative to the location of this Python script.
    design.set_dataroot("mlir", __file__)

    # Configure the fileset for the design. In an HLS flow, the "rtl" fileset
    # can be used to hold high-level language source files instead of Verilog/VHDL.
    with design.active_dataroot("mlir"), design.active_fileset("rtl"):
        # Define the name of the top-level function or kernel to be synthesized.
        design.set_topmodule("main_kernel")
        # Add the source file. Here, we're using a `.ll` file, which is
        # LLVM Intermediate Representation. This is the input that the HLS
        # tool (in this case, based on MLIR) will convert into Verilog.
        design.add_file("main_kernel.ll")

    # --- Project Setup ---
    # An ASICProject links the design's sources to a specific physical
    # implementation flow and target technology.
    project = ASICProject(design)

    # Tell the project which fileset to use for the run.
    project.add_fileset("rtl")

    # Load the target configuration. This sets up the project for the
    # FreePDK45 technology and its associated libraries and tools.
    project.load_target(freepdk45_demo.setup)

    # --- Flow Configuration ---
    # Set the flow to 'HLSASICFlow'. This is the key step. Instead of a
    # standard RTL-to-GDSII flow, this flow inserts an HLS tool (like Polygeist/MLIR)
    # at the beginning to automatically generate the RTL from the `.ll` source file.
    # The generated Verilog is then passed to the rest of the standard ASIC flow
    # (syn, place, route, etc.).
    project.set_flow(HLSASICFlow())

    # --- Execution ---
    # Run the complete HLS and ASIC flow.
    project.run()

    # --- Analysis ---
    # Display a summary of the final results, including timing, area, and power metrics.
    project.summary()

    return project


# This is the main entry point when the script is executed.
if __name__ == '__main__':
    main()
