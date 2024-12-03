#!/usr/bin/env python3
# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

import os
import siliconcompiler
from siliconcompiler.targets import interposer_demo


def main():
    '''
    Simple interposer example.
    '''
    root = os.path.dirname(__file__)

    chip = siliconcompiler.Chip('interposer')
    chip.input(os.path.join(root, "interposer.v"),
               fileset='netlist')

    chip.set('option', 'quiet', True)
    chip.set('option', 'track', True)
    chip.set('option', 'hash', True)
    chip.set('option', 'nodisplay', True)
    chip.set('constraint', 'outline', [(0, 0), (500.0, 1000.0)])
    chip.set('tool', 'openroad', 'task', 'rdlroute', 'file', 'rdlroute',
             os.path.join(root, "bumps.tcl"))
    chip.use(interposer_demo)

    chip.set('tool', 'openroad', 'version', '>=v2.0-17475', step='rdlroute', index='0')

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
