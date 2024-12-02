#!/usr/bin/env python3
# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
from siliconcompiler.flows import screenshotflow


def main(manifest='build/gcd/job0/gcd.pkg.json'):
    '''Simple screenshotflow example.'''

    chip = siliconcompiler.Chip('gcd')
    chip.read_manifest(manifest)

    chip.use(screenshotflow)
    chip.set('option', 'flow', 'screenshotflow')
    chip.set('option', 'jobname', 'highres')

    chip.input(chip.find_result('gds', jobname='job0', step='write.gds'))

    xbins = 2
    ybins = 2

    # Setup prepare
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'delete_layers', '2/0')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'delete_layers', '3/0')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'delete_layers', '4/0')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'delete_layers', '5/0')

    chip.set('tool', 'klayout', 'task', 'operations', 'var', 'merge_shapes', 'all')

    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'delete_layers:tool,klayout,task,operations,var,delete_layers')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'flatten')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'merge_shapes:tool,klayout,task,operations,var,merge_shapes')

    # Setup screenshot
    chip.set('tool', 'klayout', 'task', 'screenshot', 'var', 'xbins', str(xbins))
    chip.set('tool', 'klayout', 'task', 'screenshot', 'var', 'ybins', str(ybins))
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'hide_layers', '235/0')

    # Setup screenshot
    chip.set('tool', 'montage', 'task', 'tile', 'var', 'xbins', str(xbins))
    chip.set('tool', 'montage', 'task', 'tile', 'var', 'ybins', str(ybins))

    chip.run()


if __name__ == '__main__':
    main()
