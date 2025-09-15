#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# Import necessary classes from the siliconcompiler library.
from siliconcompiler import Design
from siliconcompiler import ASICProject
from siliconcompiler.project import LintProject

# Import pre-defined flows and targets.
from siliconcompiler.flows.lintflow import LintFlow
from siliconcompiler.targets import asic_target

# Import a library component (SRAM) to be used in the design.
from lambdalib.ramlib import Spram


class PicoRV32Design(Design):
    """
    This class defines the design sources and constraints for the PicoRV32 core.
    It inherits from Design, which is a base class for encapsulating
    all design-specific information.
    """
    def __init__(self):
        # Initialize the parent Design class.
        super().__init__()
        # Set the name of the design. This is used for file naming and organization.
        self.set_name("picorv32")

        # Define data sources using 'dataroots'. This tells SiliconCompiler where to find files.
        # Here, we're fetching the picorv32 source code directly from its GitHub repository
        # at a specific commit hash to ensure reproducibility.
        self.set_dataroot('picorv32',
                          'git+https://github.com/YosysHQ/picorv32.git',
                          'c0acaebf0d50afc6e4d15ea9973b60f5f4d03c42')
        # We also define a dataroot for local files associated with this example script.
        self.set_dataroot('example', __file__)

        # A 'fileset' is a collection of files for a specific purpose (e.g., RTL, constraints).
        # This block defines the base RTL fileset.
        with self.active_fileset("rtl"):
            # Set the active data source for the following files.
            with self.active_dataroot("picorv32"):
                # Define the top-level module for this configuration.
                self.set_topmodule("picorv32")
                # Add the main Verilog source file to the fileset.
                self.add_file("picorv32.v")

        # This block defines a more complex RTL configuration that includes a memory.
        with self.active_fileset("rtl.memory"):
            # Add the picorv32 core Verilog file.
            with self.active_dataroot("picorv32"):
                # The top module for this version is a wrapper.
                self.set_topmodule("picorv32_top")
                self.add_file("picorv32.v")
            # Add local wrapper files.
            with self.active_dataroot("example"):
                self.add_file("picorv32_top.v")
                # This is a key feature: it declares that this fileset depends on the
                # 'rtl' fileset from the 'Spram' design. SiliconCompiler will automatically
                # pull in and compile the SRAM module.
                self.add_depfileset(Spram(), "rtl")

        # Define Synopsys Design Constraints (SDC) for different PDKs.
        # SDC files provide timing constraints like clock definitions.
        with self.active_fileset("sdc.freepdk45"):
            with self.active_dataroot("example"):
                self.add_file("picorv32.sdc")

        with self.active_fileset("sdc.asap7"):
            with self.active_dataroot("example"):
                self.add_file("picorv32.sdc")

        with self.active_fileset("sdc.gf180"):
            with self.active_dataroot("example"):
                self.add_file("picorv32.sdc")


def lint(fileset: str = "rtl"):
    """
    Configures and runs a linting flow on the design.
    Linting checks the code for stylistic errors, syntax issues, and common mistakes.
    """
    # Create a project specifically for linting.
    project = LintProject()

    # Load the design configuration defined in the PicoRV32Design class.
    project.set_design(PicoRV32Design())
    # Specify which fileset to use for the linting process.
    project.add_fileset(fileset)
    # Set the flow to the pre-defined 'LintFlow'.
    project.set_flow(LintFlow())

    # Run the flow.
    project.run()
    # Display a summary of the results.
    project.summary()


def syn(fileset: str = "rtl", pdk: str = "freepdk45"):
    """
    Configures and runs a synthesis flow.
    Synthesis converts the RTL code into a gate-level netlist using a specific PDK.
    """
    # Create a standard ASIC project.
    project = ASICProject()

    # Load the design configuration.
    project.set_design(PicoRV32Design())
    # Add the RTL fileset to the project.
    project.add_fileset(fileset)

    # Load the target technology settings. This includes PDK information,
    # standard cell libraries, and tool configurations.
    project.load_target(asic_target, pdk=pdk)
    # Specify the 'synflow', which is a pre-defined flow for synthesis.
    project.set_flow("synflow")

    # Run the synthesis flow.
    project.run()
    # Display a summary of timing, area, and other metrics.
    project.summary()


def asic(fileset: str = "rtl", pdk: str = "freepdk45"):
    """
    Configures and runs the full default ASIC flow (synthesis, place-and-route, etc.).
    """
    # Create a standard ASIC project.
    project = ASICProject()

    # Load the design configuration.
    project.set_design(PicoRV32Design())
    # Add the RTL fileset.
    project.add_fileset(fileset)
    # Add the corresponding SDC fileset for the selected PDK. This is crucial for timing.
    project.add_fileset(f"sdc.{pdk}")

    # Load the target technology settings for the chosen PDK.
    project.load_target(asic_target, pdk=pdk)

    # Run the default flow defined in the target (usually a full ASIC flow).
    project.run()
    # Display a summary of the final results.
    project.summary()
    # Save the project state (results, logs, etc.) to a file for later inspection.
    project.snapshot()


def check():
    """
    A helper function to verify that all file paths defined in the schema are correct and
    accessible.
    """
    assert PicoRV32Design().check_filepaths()


# This is the main entry point when the script is executed from the command line.
if __name__ == "__main__":
    # By default, this script will run the synthesis flow.
    # You can change this to run other functions, for example:
    # lint()
    # asic(fileset="rtl.memory", pdk="asap7")
    syn()
