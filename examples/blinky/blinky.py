#!/usr/bin/env python3

# Import the necessary classes for an FPGA project. Note the use of
# FPGAProject, which is specific to FPGA flows.
from siliconcompiler import FPGAProject, Design
# Import a pre-defined flow for FPGAs.
from siliconcompiler.flows import fpgaflow
from siliconcompiler.fpgas.lattice_ice40 import ICE40Up5k_sg48


def main():
    '''
    This script demonstrates a standard RTL-to-bitstream flow for an FPGA.

    It takes a Verilog design for a simple "blinky" circuit, compiles it
    for a specific iCE40 FPGA part, and generates a bitstream file that

    can be programmed onto the hardware.
    '''

    # --- Design Setup ---
    # Create a design schema to hold the project's configuration.
    design = Design("blinky")
    # Set up a 'dataroot' to easily reference local files.
    design.set_dataroot("blinky", __file__)

    # Configure the "rtl" (Register-Transfer Level) fileset.
    with design.active_dataroot("blinky"), design.active_fileset("rtl"):
        design.set_topmodule("blinky")
        design.add_file("blinky.v")

    # Configure the "pcf" (Physical Constraints File) fileset.
    # This is a crucial file for FPGAs. It maps the ports in the Verilog
    # design (e.g., 'clk', 'led') to the physical pins on the FPGA chip.
    with design.active_dataroot("blinky"), design.active_fileset("pcf"):
        design.add_file("icebreaker.pcf")

    # --- Project Setup ---
    # Create an FPGAProject, which is tailored for FPGA-specific needs.
    project = FPGAProject(design)

    # Tell the project which filesets are required for this compilation.
    project.add_fileset("rtl")
    project.add_fileset("pcf")

    # --- FPGA Target Configuration ---
    # Apply this FPGA configuration to the project.
    project.set_fpga(ICE40Up5k_sg48())

    # --- Flow Loading ---
    # Set the compilation flow. The FPGANextPNRFlow is a pre-built flow
    # that uses open-source tools like Yosys for synthesis and nextpnr
    # for place-and-route.
    project.set_flow(fpgaflow.FPGANextPNRFlow())

    # --- Execution & Analysis ---
    # Run the entire FPGA flow. This will synthesize the RTL, place and route
    # the design onto the FPGA fabric, and generate a final bitstream file.
    # The 'assert' will cause the script to exit if the run fails.
    assert project.run()

    # Display a summary of the results. For FPGAs, this typically includes
    # a report on resource utilization (how many LUTs, FFs, etc. were used).
    project.summary()

    return project


if __name__ == '__main__':
    main()
