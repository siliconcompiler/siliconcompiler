#!/usr/bin/env python3

import siliconcompiler
import os
from siliconcompiler.targets import freepdk45_demo


def main():
    root = os.path.dirname(__file__)
    chip = siliconcompiler.Chip('gcd')
    chip.input(os.path.join(root, "gcd.c"))
    # default Bambu clock pin is 'clock'
    chip.clock(pin='clock', period=5)
    chip.load_target(freepdk45_demo)
    chip.run()
    chip.summary()
    chip.show()


if __name__ == '__main__':
    main()
