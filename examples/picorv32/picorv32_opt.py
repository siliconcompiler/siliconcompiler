#!/usr/bin/env python3
# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import siliconcompiler
from siliconcompiler.targets import skywater130_demo
from siliconcompiler.optimizer.vizier import VizierOptimizier


def main(target=skywater130_demo):
    '''RTL2GDS flow'''

    # CREATE OBJECT
    chip = siliconcompiler.Chip('picorv32')

    # SETUP
    chip.use(target)

    chip.register_source(name='picorv32',
                         path='git+https://github.com/YosysHQ/picorv32.git',
                         ref='c0acaebf0d50afc6e4d15ea9973b60f5f4d03c42')

    chip.input('picorv32.v', package='picorv32')

    chip.set('option', 'quiet', True)
    chip.set('option', 'remote', False)

    chip.clock('clk', period=25)

    opt = VizierOptimizier(chip)
    opt.add_parameter(
        ['constraint', 'density'],
        values={"min": 1, "max": 99},
        step="floorplan.init")
    opt.add_parameter(
        ['datasheet', 'pin', 'clk', 'tperiod', 'global'],
        values={"min": 5e-9, "max": 30e-9}
    )

    def cellarea(value):
        return value > 100e6
    opt.add_assertion(["metric", "cellarea"], cellarea, step='syn', index='0')
    opt.add_goal(
        ["metric", "fmax"],
        goal="max",
        stop_goal=40e6,
        step="cts.repair_timing",
        index="0"
    )
    # chip.set('option', 'scheduler', 'maxcores', 4)

    opt.run(experiments=20, parallel=1)
    opt.report()


if __name__ == '__main__':
    main()
