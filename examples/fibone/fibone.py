#!/usr/bin/env python3

import siliconcompiler
import os


def main():
    root = os.path.dirname(__file__)
    chip = siliconcompiler.Chip('mkFibOne')
    chip.input(os.path.join(root, "FibOne.bsv"))
    # default Bluespec clock pin is 'CLK'
    chip.clock(pin='CLK', period=5)
    chip.load_target("freepdk45_demo")
    chip.run()
    chip.summary()
    chip.show()


if __name__ == '__main__':
    main()
