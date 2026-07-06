#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

"""
Example demonstrating cocotb integration with SiliconCompiler.

This example shows how to use the ``cocotb_dvflow`` helper to run Python-based
cocotb testbenches against a design, using either the Icarus Verilog or
Verilator simulation flow.
"""

from siliconcompiler import Design, Sim

from siliconcompiler.targets.cocotb_dvflow import cocotb_dvflow


class Adder(Design):
    """RTL design schema for the parameterized adder.

    Defines the ``rtl`` fileset containing the Verilog source and its
    top module for the adder design under test.
    """

    def __init__(self):
        """Initializes the Adder object."""
        super().__init__()

        self.set_name("adder")

        self.set_dataroot("local", __file__)

        with self.active_dataroot("local"):
            with self.active_fileset("rtl"):
                self.set_topmodule("adder")
                self.add_file("adder.v")
                self.set_param("WIDTH", "8")


class AdderTb(Design):
    """Cocotb testbench schema for the adder design.

    Defines the ``testbench.cocotb`` fileset containing the Python cocotb
    test module and declares a dependency on the :class:`Adder` RTL design.
    """

    def __init__(self):
        """Initializes the AdderTb object."""
        super().__init__()

        # Set the design's name
        self.set_name("adder_testbench")

        # Establish the root directory for all design-related files
        self.set_dataroot("local", __file__)

        # Configure filesets within the established data root
        with self.active_dataroot("local"):
            with self.active_fileset("testbench.cocotb"):
                self.set_topmodule("adder")
                self.add_file("cocotb_adder.py", filetype="python")
                self.add_depfileset(Adder(), "rtl")


def sim_icarus(seed: int = None, trace: bool = True):
    """Runs a cocotb simulation of the Adder design.

    Args:
        seed (int, optional): Random seed for test reproducibility.
            If not set, cocotb will generate a random seed.
        trace (bool, optional): Enable waveform tracing. Defaults to True.
            When enabled, generates a VCD file for waveform viewing.
    """
    # Create a project instance
    project = Sim(AdderTb())

    # Add the cocotb testbench files
    project.add_fileset("testbench.cocotb")

    # Call cocotb target function to setup the project for a cocotb run
    cocotb_dvflow(
        project=project,
        trace=trace,
        timescale=("1ns", "1ps"),
        seed=seed
    )

    # Select the icarus + cocotb flow
    project.set_flow("icaruscocotbdvflow")

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


def sim_verilator(seed: int = None, trace: bool = True, trace_type: str = "vcd"):
    """Runs a cocotb simulation of the Adder design using Verilator.

    Args:
        seed (int, optional): Random seed for test reproducibility.
            If not set, cocotb will generate a random seed.
        trace (bool, optional): Enable waveform tracing. Defaults to True.
            When enabled, generates a waveform file for viewing.
        trace_type (str, optional): Waveform format - 'vcd' (default) or 'fst'.
            FST is a compressed format that produces smaller files.
    """
    # Create a project instance
    project = Sim(AdderTb())

    # Add the cocotb testbench files
    project.add_fileset("testbench.cocotb")

    # Call cocotb target function to setup the project for a cocotb run
    cocotb_dvflow(
        project=project,
        trace=trace,
        trace_type=trace_type,
        timescale=("1ns", "1ps"),
        seed=seed
    )

    # Select the Verilator + cocotb flow
    project.set_flow("verilatorcocotbdvflow")

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
    wave_ext = trace_type if trace_type in ("vcd", "fst") else "vcd"
    wave = project.find_result(
        step='simulate',
        index='0',
        directory="reports",
        filename=f"adder.{wave_ext}"
    )
    if wave:
        print(f"Waveform file: {wave}")


def check():
    """Checks that all file paths in the AdderTb design are valid."""
    assert AdderTb().check_filepaths()
