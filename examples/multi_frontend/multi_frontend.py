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

    chip.set('tool', 'chisel', 'task', 'convert', 'var', 'module', 'GCD_Scala')
    chip.set('tool', 'bambu', 'task', 'convert', 'var', 'module', 'gcd_cpp')

    chip.clock('clk', 20)

    chip.set('option', 'strict', True)

    chip.load_target(skywater130_demo)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
