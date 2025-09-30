#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Design, FPGADevice
from siliconcompiler import Lint, Sim
from siliconcompiler import ASIC, FPGA

from siliconcompiler.flows.lintflow import LintFlow
from siliconcompiler.flows.dvflow import DVFlow
from siliconcompiler.flows.fpgaflow import FPGAXilinxFlow

from siliconcompiler.targets import asic_target


class HeartbeatDesign(Design):
    """Heartbeat design schema setup.

    This class defines the project structure for the 'heartbeat' design,
    configuring source files, parameters, and constraints for various

    tool flows and technology targets. By encapsulating the design setup,
    it allows for easy reuse across different flows (lint, sim, asic, fpga).
    """
    def __init__(self):
        """Initializes the HeartbeatDesign object.

        This method sets up all the necessary filesets for RTL,
        simulation testbenches (Icarus and Verilator), and technology-specific
        constraint files (SDC for ASIC, XDC for FPGA).
        """
        super().__init__()
        # Set the design's name.
        self.set_name("heartbeat")

        # Establish the root directory for all design-related files.
        self.set_dataroot("heartbeat", __file__)

        # Configure filesets within the established data root.
        with self.active_dataroot("heartbeat"):
            # RTL sources
            with self.active_fileset("rtl"):
                self.set_topmodule("heartbeat")
                self.add_file("heartbeat.v")
                self.set_param("N", "8")  # Default parameter value

            # Testbench for Icarus Verilog
            with self.active_fileset("testbench.icarus"):
                self.set_topmodule("heartbeat_tb")
                self.add_file("testbench.v")
                self.set_param("N", "8")

            # C++ Testbench for Verilator
            with self.active_fileset("testbench.verilator"):
                self.set_topmodule("heartbeat")
                self.add_file("testbench.cc")
                self.set_param("N", "8")

            # ASIC timing constraints for the FreePDK45 technology.
            with self.active_fileset("rtl.freepdk45"):
                self.add_file("heartbeat.sdc")

            # ASIC timing constraints for the ASAP7 technology.
            with self.active_fileset("rtl.asap7"):
                self.add_file("heartbeat_asap7.sdc")

            # FPGA timing and pin constraints for a Xilinx Artix-7 device.
            with self.active_fileset("fpga.xc7a100tcsg324"):
                self.add_file("heartbeat.xdc")


def lint(N: str = None):
    """Runs the linting flow on the Heartbeat design.

    Linting checks the Verilog source code for syntax errors and style
    issues without performing a full synthesis.

    Args:
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
    """
    # Create a project instance tailored for linting.
    project = Lint()

    # Instantiate the design configuration.
    hb = HeartbeatDesign()

    # Associate the design with the project.
    project.set_design(hb)
    # Add the necessary fileset for this flow.
    project.add_fileset("rtl")

    # Optionally override the 'N' parameter from the command line.
    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    # Configure the project to use the linting flow.
    project.set_flow(LintFlow())

    # Execute the flow.
    project.run()
    # Display a summary of the results.
    project.summary()


def syn(pdk: str = "freepdk45", N: str = None):
    """Runs the synthesis flow for the Heartbeat design.

    Synthesis converts the RTL Verilog code into a gate-level netlist
    using a specific Process Design Kit (PDK).

    Args:
        pdk (str, optional): The process design kit (PDK) to target.
            Defaults to "freepdk45".
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
    """
    # Create a project instance for an ASIC flow.
    project = ASIC()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    # Add the RTL source files and the technology-specific constraint files.
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")

    # Optionally override the 'N' parameter.
    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    # Load the target configuration for the specified PDK.
    asic_target(project, pdk=pdk)
    # Specify the synthesis flow.
    project.set_flow("synflow")

    # Run the flow and display the summary.
    project.run()
    project.summary()


def asic(pdk: str = "freepdk45", N: str = None):
    """Runs the full ASIC implementation flow for the Heartbeat design.

    This flow includes synthesis, floorplanning, placement, clock tree synthesis,
    and routing. It concludes by saving a snapshot of the final design layout.

    Args:
        pdk (str, optional): The process design kit (PDK) to target.
            Defaults to "freepdk45".
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
    """
    # Create a project instance for an ASIC flow.
    project = ASIC()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    # Add the necessary filesets.
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")

    # Optionally override the 'N' parameter.
    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    # Load the target, which automatically selects the default 'asicflow'.
    asic_target(project, pdk=pdk)

    # Run the full place-and-route flow.
    project.run()
    # Display a summary of timing, power, and area results.
    project.summary()
    # Save the final layout and project configuration.
    project.snapshot()


def sim(N: str = None, tool: str = "verilator"):
    """Runs a simulation of the Heartbeat design.

    After the simulation completes, it attempts to open the generated
    waveform file (VCD) for viewing.

    Args:
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
        tool (str, optional): The simulation tool to use ('verilator' or
            'icarus'). Defaults to "verilator".
    """
    # Create a project instance tailored for simulation.
    project = Sim()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    # Add the tool-specific testbench and the RTL design files.
    project.add_fileset(f"testbench.{tool}")
    project.add_fileset("rtl")
    # Set the appropriate design verification flow.
    project.set_flow(DVFlow(tool=tool))

    # Optionally override the 'N' parameter for the testbench.
    if N is not None:
        hb.set_param("N", N, fileset=f"testbench.{tool}")

    # Run the simulation.
    project.run()
    project.summary()

    # Find the VCD (Value Change Dump) waveform file from the results.
    vcd = project.find_result(step='simulate', index='0',
                              directory="reports",
                              filename="heartbeat_tb.vcd")
    # If a VCD file is found, open it with the default waveform viewer.
    if vcd:
        project.show(vcd)


def fpga(N: str = None):
    """Runs the FPGA implementation flow for the Heartbeat design.

    This flow targets a Xilinx Artix-7 FPGA (xc7a100tcsg324) and generates
    a bitstream that can be programmed onto the device.

    Args:
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
    """
    # Create a project instance for an FPGA flow.
    project = FPGA()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    # Add the RTL and FPGA constraint filesets.
    project.add_fileset("rtl")
    project.add_fileset("fpga.xc7a100tcsg324")
    # Specify the Xilinx implementation flow.
    project.set_flow(FPGAXilinxFlow())

    # Configure the specific FPGA part details.
    fpga = FPGADevice("xc7")
    fpga.set_partname("xc7a100tcsg324")
    project.set_fpga(fpga)

    # Optionally override the 'N' parameter.
    if N is not None:
        hb.set_param("N", N, fileset="testbench")

    # Run the FPGA flow (synthesis, place, route, bitstream generation).
    project.run()
    project.summary()


def check():
    """Checks that all file paths in the HeartbeatDesign are valid.

    This is a simple utility function to ensure that all source files
    referenced in the design schema actually exist.
    """
    assert HeartbeatDesign().check_filepaths()


if __name__ == "__main__":
    # When the script is executed directly from the command line,
    # run the synthesis flow by default.
    syn()
