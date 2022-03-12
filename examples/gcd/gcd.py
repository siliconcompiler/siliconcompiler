# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler

def main():
    '''Simple asicflow example.'''

    chip = siliconcompiler.Chip(design='gcd', loglevel='INFO')
    chip.add('source', 'gcd.v')
    chip.add('constraint', 'gcd.sdc')
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('track', True)
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.load_target("freepdk45_demo")
    chip.run()
    chip.summary()

if __name__ == '__main__':
    main()