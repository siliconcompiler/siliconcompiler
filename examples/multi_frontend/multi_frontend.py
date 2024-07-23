#!/usr/bin/env python3

import siliconcompiler
from siliconcompiler.targets import skywater130_demo
import os


def main():
    chip = siliconcompiler.Chip('top')
    root = os.path.dirname(__file__)
    # Add VHDL file
    chip.input(os.path.join(root, 'binary_4_bit_adder_top.vhd'))
    # Add chisel file
    chip.input(os.path.join(root, 'GCD_Scala.scala'))
    # Add hls file
    chip.input(os.path.join(root, 'gcd.c'))
    # Add bluespec file
    chip.input(os.path.join(root, 'FibOne.bsv'))
    # Add verilog file
    chip.input(os.path.join(root, 'gcd.v'))

    # Add top
    chip.input(os.path.join(root, 'top.v'))

    # this is to set -fsynopsys
    chip.set('tool', 'ghdl', 'task', 'convert', 'var', 'extraopts', '-fsynopsys')

    chip.set('option', 'entrypoint', 'binary_4_bit_adder_top', step='import_vhdl')
    chip.set('option', 'entrypoint', 'GCD_Scala', step='import_chisel')
    chip.set('option', 'entrypoint', 'gcd_cpp', step='import_c')
    chip.set('option', 'entrypoint', 'mkFibOne', step='import_bluespec')

    chip.clock('clk', 20)

    chip.set('option', 'strict', True)

    chip.load_target(skywater130_demo)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
