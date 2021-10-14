# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
import json

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

##################################
def test_minmax():
    '''API test for min/max() methods
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()
    chip.set("design", "oh_add")

    #sequence
    flowpipe = ['import',
                'syn',
                'synmin']

    tools = {
        'import': 'verilator',
        'syn': 'yosys'
    }

    N = 10

    threads = {
        'import': 1,
        'syn' : N,
        'synmin' : 1
    }

    # Parallel flow for syn
    N = 10
    for i, step in enumerate(flowpipe):
        for index in range(threads[step]):
            if step == "synmin":
                chip.set('flowgraph', step, str(index), 'function', 'step_minimum')
                for j in range(N):
                    chip.add('flowgraph', step, '0', 'input', flowpipe[i-1] + str(j))
            elif step == 'import':
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
            else:
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.set('flowgraph', step, str(index), 'input', flowpipe[i-1] + '0')
            #weight
            chip.set('flowgraph', step, str(index), 'weight',  'cellarea', 1.0)
            #goal
            chip.set('metric', step, str(index), 'setupwns', 'goal', 0.0)
            chip.set('metric', step, str(index), 'setupwns', 'real', 0.0)

    # creating fake syn results
    for index in range(N):
        for metric in chip.getkeys('flowgraph', 'syn', str(index), 'weight'):
            chip.set('metric', 'syn',str(index), metric, 'real', 1000-index*1 + 42.0)

    chip.write_flowgraph('minmax.png')
    chip.write_manifest('minmax.json')

    (score, winner) = chip.step_minimum(*[f'syn{i}' for i in range(N)])
    assert winner == 'syn9'

    # TODO: fix step_maximum
    # (score, winner) = chip.step_maximum(*[f'syn{i}' for i in range(N)])
    # assert winner == 'syn0'

#########################
if __name__ == "__main__":
    test_minmax()
