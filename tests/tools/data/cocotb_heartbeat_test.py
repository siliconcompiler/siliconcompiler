import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import random


@cocotb.test()
async def simple_test(dut):
    """Test heartbeat verilog module"""

    # Get width of R/W registers
    reg_width = dut.N.value

    # Start clock
    clk = Clock(dut.clk, 10.0, units="ns")
    await cocotb.start(clk.start())

    await Timer(100, units="ns")

    # Wait some cycles before starting test
    await ClockCycles(dut.clk, 10)
