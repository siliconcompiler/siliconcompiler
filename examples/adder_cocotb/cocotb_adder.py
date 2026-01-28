"""Cocotb testbench for the adder module."""

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def adder_basic_test(dut):
    """Test basic addition operations."""
    # Test 0 + 0 = 0
    dut.a.value = 0
    dut.b.value = 0
    await Timer(1, unit="ns")
    assert dut.sum.value == 0, f"Expected 0, got {dut.sum.value}"

    # Test 1 + 1 = 2
    dut.a.value = 1
    dut.b.value = 1
    await Timer(1, unit="ns")
    assert dut.sum.value == 2, f"Expected 2, got {dut.sum.value}"

    # Test 5 + 3 = 8
    dut.a.value = 5
    dut.b.value = 3
    await Timer(1, unit="ns")
    assert dut.sum.value == 8, f"Expected 8, got {dut.sum.value}"


@cocotb.test()
async def adder_overflow_test(dut):
    """Test addition with overflow (result uses extra bit)."""
    # Test 255 + 1 = 256 (overflow into 9th bit)
    dut.a.value = 255
    dut.b.value = 1
    await Timer(1, unit="ns")
    assert dut.sum.value == 256, f"Expected 256, got {dut.sum.value}"

    # Test 255 + 255 = 510
    dut.a.value = 255
    dut.b.value = 255
    await Timer(1, unit="ns")
    assert dut.sum.value == 510, f"Expected 510, got {dut.sum.value}"


@cocotb.test()
async def adder_random_test(dut):
    """Test addition with random values."""
    import random

    for _ in range(10):
        a = random.randint(0, 255)
        b = random.randint(0, 255)
        expected = a + b

        dut.a.value = a
        dut.b.value = b
        await Timer(1, unit="ns")

        assert dut.sum.value == expected, \
            f"Failed: {a} + {b} = {dut.sum.value}, expected {expected}"
