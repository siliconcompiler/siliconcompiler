#!/usr/bin/env python3

# Import the necessary components from the Migen library for hardware design.
# Migen allows you to describe hardware circuits using Python.
from migen import Module, Signal, Cat, Replicate
from migen.fhdl.verilog import convert

# Import the core classes from the siliconcompiler library.
from siliconcompiler import DesignSchema
from siliconcompiler import ASICProject
# Import a pre-defined target for the FreePDK45 process.
from siliconcompiler.targets import freepdk45_demo

# --- Migen Hardware Description ---
# This class defines the 'Heartbeat' hardware module using Migen's syntax.
class Heartbeat(Module):
    """
    A simple digital circuit that generates a periodic single-cycle pulse.

    This module contains a counter that increments on every clock cycle.
    The output 'out' goes high for a single clock cycle when the counter
    reaches a specific value (1 in this case) and is low otherwise.

    Args:
        N (int): The bit-width of the internal counter.
    """
    def __init__(self, N: int = 8):
        # --- I/O Declaration ---
        # Declare a 1-bit output signal for the module.
        self.out = Signal()

        # --- Internal Register Declaration ---
        # Declare an N-bit register to be used as a counter.
        self.counter_reg = Signal(N)

        ### COMBINATORIAL AND SEQUENTIAL LOGIC ###

        # The 'self.sync' domain is used to describe synchronous logic
        # that updates on the positive edge of the 'sys' clock.

        # On each clock cycle, increment the counter.
        self.sync += self.counter_reg.eq(self.counter_reg + 1)

        # Describe the logic for the output signal.
        # 'Cat' concatenates signals, and 'Replicate' creates a bitstring
        # of repeated values. So, Cat(Replicate(0, N-1), 1) creates the
        # binary value '00...01'. The output 'out' will be high only
        # when the counter is exactly 1.
        self.sync += self.out.eq(self.counter_reg == Cat(Replicate(0, N - 1), 1))


def main():
    """
    Generates Verilog from a Migen module and runs it through a full
    ASIC compilation flow using SiliconCompiler.
    """
    # --- Verilog Generation ---
    # Instantiate the Migen Heartbeat module.
    heartbeat = Heartbeat()
    # Convert the Migen module into a Verilog file.
    # The `convert` function translates the Python hardware description
    # into standard Verilog HDL. We name the output module 'heartbeat'
    # and write it to 'heartbeat.v'.
    convert(heartbeat, ios={heartbeat.out}, name='heartbeat').write('heartbeat.v')

    # --- SiliconCompiler Design Setup ---
    # Create a design object to hold the configuration.
    design = DesignSchema("heartbeat")

    # Set the root directory for this design's source files using its filepath.
    design.set_dataroot("heartbeat", __file__)

    # Configure the RTL (Verilog) source files. A 'fileset' is a collection
    # of files for a specific purpose.
    with design.active_fileset("rtl"):
        # Set the name of the top-level module.
        design.set_topmodule("heartbeat")
        # Add the Verilog file we just generated.
        design.add_file("heartbeat.v")

    # Configure the SDC (Synopsys Design Constraints) file for timing.
    # This fileset is separate from the RTL.
    with design.active_dataroot("heartbeat"), design.active_fileset("sdc"):
        design.add_file("heartbeat.sdc")

    # --- SiliconCompiler Project Setup ---
    # Create an ASIC project from the design configuration.
    project = ASICProject(design)

    # Tell the project which filesets are needed for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the FreePDK45 demo process.
    # This configures the project with the correct PDK, standard cell libraries,
    # and tool flow for this technology.
    project.load_target(freepdk45_demo.setup)

    # --- Execution & Analysis ---
    # Execute the complete ASIC compilation flow (synthesis, place, route, etc.).
    project.run()

    # Print a summary of the results (timing, area, power, etc.).
    project.summary()

    # Display the final physical layout in a GDS viewer (like KLayout).
    project.show()


if __name__ == '__main__':
    main()
