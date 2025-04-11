#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

import os
import siliconcompiler
from siliconcompiler.targets import ihp130_demo

from siliconcompiler.tools.klayout import drc, convert_drc_db


def main():
    '''Simple asicflow example.'''
    root = os.path.dirname(__file__)

    chip = siliconcompiler.Chip('gcd')
    chip.input(os.path.join(root, "gcd.v"))
    chip.input(os.path.join(root, "gcd.sdc"))
    chip.set('option', 'quiet', True)
    chip.set('option', 'track', True)
    chip.set('option', 'hash', True)
    chip.set('option', 'nodisplay', True)
    chip.use(ihp130_demo)
    chip.run()
    chip.summary()

    gds_path = chip.find_result('gds', step='write.gds')
    chip.set('option', 'jobname', 'signoff')

    flow = siliconcompiler.Flow('drcflow')
    flow.node('drcflow', 'drc', drc)
    flow.node('drcflow', 'convert', convert_drc_db)
    flow.edge('drcflow', 'drc', 'convert')

    chip.use(flow)

    chip.set('option', 'flow', 'drcflow')
    chip.input(gds_path)

    chip.set('tool', 'klayout', 'task', 'drc', 'var', 'drc_name', 'minimal')
    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
