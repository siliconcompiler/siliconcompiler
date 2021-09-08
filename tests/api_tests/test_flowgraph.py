# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
import re
import os

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_flowgraph():


    tools = {
        'import': 'verilator',
        'syn': 'yosys',
        'apr': 'openroad',
        'floorplan': 'openroad',
        'physys': 'openroad',
        'place': 'openroad',
        'cts': 'openroad',
        'route': 'openroad',
        'dfm': 'openroad',
        'export': 'klayout'
    }

    ################################################
    # Serial
    ################################################
    flow = ['import',
            'syn',
            'apr',
            'export']

    chip = siliconcompiler.Chip(loglevel="INFO")

    for i in range(len(flow)):
        step = flow[i]
        chip.set('flowgraph', step, '0', 'tool', tools[step])
        if step != 'import':
            chip.add('flowgraph', step, '0', 'input', flow[i-1], str(0))

    chip.writegraph('serial.png')

    ################################################
    # Fork-Join
    ################################################

    flow = ['import',
            'syn',
            'syn_minimum',
            'floorplan',
            'floorplan_minimum',
            'physys',
            'physys_minimum',
            'cts',
            'cts_minimum',
            'route',
            'route_minimum',
            'export']

    N = 4
    chip = siliconcompiler.Chip(loglevel="INFO")

    for i in range(len(flow)):
        step = flow[i]
        if step == 'import':
            chip.set('flowgraph', step, str(0), 'tool', tools[step])
        elif step == 'export':
            chip.add('flowgraph', step, str(0), 'input', 'route_minimum', '0')
            chip.set('flowgraph', step, str(0), 'tool', tools[step])
        elif re.search(r'minimum', step):
            chip.set('flowgraph', step, str(0), 'tool', 'builtin')
            chip.set('flowgraph', step, str(0), 'function', 'minimum')
            for index in range(N):
                chip.add('flowgraph', step, str(0), 'input', flow[i-1], str(index))
        else:
            for index in range(N):
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.add('flowgraph', step, str(index), 'input', flow[i-1], '0')

    chip.writegraph('forkjoin.png')

    ################################################
    # Pipes
    ################################################
    flow = ['import',
            'syn',
            'apr',
            'apr_minimum',
            'export']

    N = 4
    chip = siliconcompiler.Chip(loglevel="INFO")

    for i in range(len(flow)):
        step = flow[i]
        if step == 'import':
            chip.set('flowgraph', step, str(0), 'tool', tools[step])
        elif step == 'syn':
            for index in range(N):
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.add('flowgraph', step, str(index), 'input', flow[i-1], '0')
        elif step == 'apr':
            for index in range(N):
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.add('flowgraph', step, str(index), 'input', 'syn', str(index))
        elif step == 'apr_minimum':
            chip.set('flowgraph', step, str(0), 'tool', 'builtin')
            chip.set('flowgraph', step, str(0), 'function', 'minimum')
            for index in range(N):
                chip.add('flowgraph', step, str(0), 'input', 'apr', str(index))
        elif step == 'export':
            chip.set('flowgraph', step, str(0), 'tool', tools[step])
            chip.add('flowgraph', step, str(0), 'input', 'apr_minimum', str(0))

    chip.writegraph('pipes.png')

    # basic compile to end check
    os.path.isfile('pipes.png')
    os.path.isfile('forkjoin.png')
    os.path.isfile('serial.png')

#########################
if __name__ == "__main__":
    test_flowgraph()
