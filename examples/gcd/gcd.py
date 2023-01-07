#!/usr/bin/env python3
# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
import os

def main(root='.'):
    '''Simple asicflow example.'''

    chip = siliconcompiler.Chip('gcd')
    chip.add('input', 'verilog', f"{root}/gcd.v")
    chip.add('input', 'sdc', f"{root}/gcd.sdc")
    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)
    chip.set('option', 'track', True)
    chip.set('option', 'skipcheck', True)
    chip.set('option', 'novercheck', True)
    chip.set('option', 'nodisplay', True)
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.load_target("freepdk45_demo")
    chip.run()
    chip.summary()

if __name__ == '__main__':
    main(root=os.path.dirname(__file__))
