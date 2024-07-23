#!/usr/bin/env python3

import siliconcompiler
import os


def main():
    chip = siliconcompiler.Chip('binary_4_bit_adder_top')
    root = os.path.dirname(__file__)
    chip.input(os.path.join(root, "binary_4_bit_adder_top.vhd"))
    # this is to set -fsynopsys
    # see PR #1015 (https://github.com/siliconcompiler/siliconcompiler/pull/1015)
    chip.set('tool', 'ghdl', 'task', 'convert', 'var', 'extraopts', '-fsynopsys')

    chip.load_target("freepdk45_demo")

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
