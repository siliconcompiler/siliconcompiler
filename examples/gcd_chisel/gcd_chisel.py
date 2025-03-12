#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('GCD')
    chip.register_source("gcd-chisel-example", __file__)
    chip.input("GCD.scala", package="gcd-chisel-example")
    # default Chisel clock pin is 'clock'
    chip.clock(pin='clock', period=5)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()
    chip.show()


if __name__ == '__main__':
    main()
