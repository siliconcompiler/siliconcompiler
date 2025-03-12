#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('gcd')
    chip.register_source("gcd-hls-example", __file__)
    chip.input("gcd.c", package="gcd-hls-example")
    # default Bambu clock pin is 'clock'
    chip.clock(pin='clock', period=5)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()
    chip.show()


if __name__ == '__main__':
    main()
