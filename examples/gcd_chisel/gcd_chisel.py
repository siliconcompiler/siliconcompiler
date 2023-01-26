#!/usr/bin/env python3

import siliconcompiler
from siliconcompiler.targets import freepdk45_demo

def main():
    chip = siliconcompiler.Chip('GCD')
    chip.input('GCD.scala')
    chip.set('option', 'frontend', 'chisel')
    # default Chisel clock pin is 'clock'
    chip.clock(pin='clock', period=5)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()
    chip.show()

if __name__ == '__main__':
    main()
