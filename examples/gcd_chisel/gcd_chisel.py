#!/usr/bin/env python3

import siliconcompiler

def main():
    chip = siliconcompiler.Chip('GCD')
    chip.set('input', 'scala', 'GCD.scala')
    chip.set('option', 'frontend', 'chisel')
    # default Chisel clock pin is 'clock'
    chip.clock(pin='clock', period=5)
    chip.load_target('freepdk45_demo')
    chip.run()
    chip.summary()
    chip.show()

if __name__ == '__main__':
    main()
