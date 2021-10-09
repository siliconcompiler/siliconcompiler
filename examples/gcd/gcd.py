# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler

def main():
    '''Simple asicflow example.'''

    chip = siliconcompiler.Chip(design='gcd', loglevel='INFO')
    chip.add('source', 'examples/gcd/gcd.v')
    chip.add('constraint', "examples/gcd/gcd.sdc")
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.target("asicflow_freepdk45")
    chip.run()
    chip.summary()

if __name__ == '__main__':
    main()