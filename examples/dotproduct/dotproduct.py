#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('mkDotProduct_nt_Int32')

    chip.register_source("dotproduct-example", __file__)
    chip.input('DotProduct_nt_Int32.bsv', package="dotproduct-example")
    chip.add('option', 'ydir', ".", package="dotproduct-example")

    chip.set('option', 'nodisplay', True)
    chip.set('option', 'quiet', True)
    chip.clock(pin='CLK', period=1)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
