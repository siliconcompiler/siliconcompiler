#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

"""
Example demonstrating cocotb integration with SiliconCompiler.

This example shows how to use the DVFlow with the 'icarus-cocotb' tool
to run Python-based cocotb testbenches against an Icarus Verilog simulation.
"""

from siliconcompiler import Design, Sim
from siliconcompiler.flows.dvflow import DVFlow
from siliconcompiler.tools.icarus.compile import CompileTask
from siliconcompiler.tools.icarus.cocotb import CocotbTask


class AdderDesign(Design):
    """Adder design schema setup.

    This class defines the project structure for a simple parameterized
    adder design with a cocotb testbench.
    """

    def __init__(self):
        """Initializes the AdderDesign object."""
        super().__init__()

        # Set the design's name
        self.set_name("adder")

        # Establish the root directory for all design-related files
        self.set_dataroot("adder", __file__)

        # Configure filesets within the established data root
        with self.active_dataroot("adder"):
            # RTL sources
            with self.active_fileset("rtl"):
                self.set_topmodule("adder")
                self.add_file("adder.v")
                self.set_param("WIDTH", "8")

            # Cocotb testbench
            with self.active_fileset("testbench.cocotb"):
                self.set_topmodule("adder")
                self.add_file("test_adder.py", filetype="python")
                self.set_param("WIDTH", "8")


def sim(seed: int = None):
    """Runs a cocotb simulation of the Adder design.

    Args:
        seed (int, optional): Random seed for test reproducibility.
            If not set, cocotb will generate a random seed.
    """
    # Create a project instance tailored for simulation
    project = Sim()

    # Instantiate and configure the design
    adder = AdderDesign()
    project.set_design(adder)

    # Add the cocotb testbench and the RTL design files
    project.add_fileset("testbench.cocotb")
    project.add_fileset("rtl")

    # Set the cocotb design verification flow
    project.set_flow(DVFlow(tool="icarus-cocotb"))

    # Enable waveform tracing
    CompileTask.find_task(project).set_trace_enabled(True)

    # Optionally set a random seed for reproducibility
    if seed is not None:
        CocotbTask.find_task(project).set_cocotb_random_seed(seed)

    # Run the simulation
    project.run()
    project.summary()

    # Find and display the results file
    results = project.find_result(
        step='simulate',
        index='0',
        directory="outputs",
        filename="results.xml"
    )
    if results:
        print(f"\nCocotb results file: {results}")

    # Find and display the waveform file
    vcd = project.find_result(
        step='simulate',
        index='0',
        directory="reports",
        filename="adder.vcd"
    )
    if vcd:
        print(f"Waveform file: {vcd}")


def check():
    """Checks that all file paths in the AdderDesign are valid."""
    assert AdderDesign().check_filepaths()
