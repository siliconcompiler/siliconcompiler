#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('top')
    chip.register_source("multi-frontend-example", __file__)
    # Add VHDL file
    chip.input('binary_4_bit_adder_top.vhd', package="multi-frontend-example")
    # Add chisel file
    chip.input('GCD_Scala.scala', package="multi-frontend-example")
    # Add hls file
    chip.input('gcd.c', package="multi-frontend-example")
    # Add bluespec file
    chip.input('FibOne.bsv', package="multi-frontend-example")
    # Add verilog file
    chip.input('gcd.v', package="multi-frontend-example")

    # Add top
    chip.input('top.v', package="multi-frontend-example")

    # this is to set -fsynopsys
    chip.set('tool', 'ghdl', 'task', 'convert', 'var', 'extraopts', '-fsynopsys')

    chip.set('option', 'entrypoint', 'binary_4_bit_adder_top', step='import.vhdl')
    chip.set('option', 'entrypoint', 'GCD_Scala', step='import.chisel')
    chip.set('option', 'entrypoint', 'gcd_cpp', step='import.c')
    chip.set('option', 'entrypoint', 'mkFibOne', step='import.bluespec')

    chip.clock('clk', 20)

    chip.set('option', 'strict', True)

    chip.use(freepdk45_demo)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
