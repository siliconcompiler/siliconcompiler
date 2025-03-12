#!/usr/bin/env python3
# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Chip
from siliconcompiler.targets import interposer_demo


def main():
    '''
    Simple interposer example.
    '''

    chip = Chip('interposer')
    chip.register_source("interposer-example", __file__)
    chip.input("interposer.v",
               fileset='netlist', package="interposer-example")

    chip.set('option', 'quiet', True)
    chip.set('option', 'track', True)
    chip.set('option', 'hash', True)
    chip.set('option', 'nodisplay', True)
    chip.set('constraint', 'outline', [(0, 0), (500.0, 1000.0)])
    chip.set('tool', 'openroad', 'task', 'rdlroute', 'file', 'rdlroute',
             "bumps.tcl", package="interposer-example")
    chip.use(interposer_demo)

    chip.run()
    chip.summary()

    gds = chip.find_result('gds', step='write_gds')

    chip.set('option', 'flow', 'drcflow')
    chip.set('option', 'jobname', 'signoff')
    chip.input(gds)
    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
