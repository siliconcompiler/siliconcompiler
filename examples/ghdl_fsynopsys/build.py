#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('binary_4_bit_adder_top')
    chip.register_source("ghdl-fsynopsys-example", __file__)
    chip.input("binary_4_bit_adder_top.vhd", package="ghdl-fsynopsys-example")
    # this is to set -fsynopsys
    # see PR #1015 (https://github.com/siliconcompiler/siliconcompiler/pull/1015)
    chip.set('tool', 'ghdl', 'task', 'convert', 'var', 'extraopts', '-fsynopsys')

    chip.use(freepdk45_demo)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
