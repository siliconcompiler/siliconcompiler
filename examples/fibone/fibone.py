#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('mkFibOne')
    chip.register_source("fibone-example", __file__)
    chip.input("FibOne.bsv", package="fibone-example")
    # default Bluespec clock pin is 'CLK'
    chip.clock(pin='CLK', period=5)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()
    chip.show()


if __name__ == '__main__':
    main()
