# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import pytest

from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic

from siliconcompiler.tools.builtin import minimum


@pytest.fixture
def chip():
    # Create instance of Chip class
    chip = siliconcompiler.Chip('oh_add')

    # sequence
    flowpipe = ['import',
                'syn',
                'teststep']

    task = {
        'import': parse,
        'syn': syn_asic,
        'teststep': minimum
    }

    N = 10
    flow = 'testflow'
    chip.set('option', 'flow', flow)

    threads = {
        'import': 1,
        'syn': N,
        'teststep': 1
    }

    # Parallel flow for syn
    for i, step in enumerate(flowpipe):
        for index in range(threads[step]):
            if step == "teststep":
                chip.node(flow, step, task[step], index=index)
                for j in range(N):
                    chip.edge(flow, flowpipe[i - 1], step, tail_index=j)
            elif step == 'import':
                chip.node(flow, step, task[step], index=index)
            else:
                chip.node(flow, step, task[step], index=index)
                chip.edge(flow, flowpipe[i - 1], step, tail_index=0, head_index=index)

            # weight
            chip.set('flowgraph', flow, step, str(index), 'weight', 'cellarea', 1.0)
            # goal
            chip.set('flowgraph', flow, step, str(index), 'goal', 'setupwns', 0.0)
            chip.set('metric', 'setupwns', 0.0, step=step, index=index)

    # creating fake syn results
    for index in range(N):
        for metric in chip.getkeys('flowgraph', flow, 'syn', str(index), 'weight'):
            if metric != 'setupwns':
                chip.set('metric', metric, 1000 - index * 1 + 42.0, step='syn', index=index)

    return chip


##################################
def test_minimum(chip):
    '''API test for min/max() methods
    '''
    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner == ('syn', '9')


def test_maximum(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'taskmodule',
             'siliconcompiler.tools.builtin.maximum')
    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner == ('syn', '0')


def test_all_failed(chip):
    flow = chip.get('option', 'flow')
    N = len(chip.getkeys('flowgraph', flow, 'syn'))

    for index in range(N):
        chip.set('flowgraph', flow, 'syn', str(index), 'status', siliconcompiler.NodeStatus.ERROR)

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner is None


def test_winner_failed(chip):
    flow = chip.get('option', 'flow')

    # set error bit on what would otherwise be winner
    chip.set('flowgraph', flow, 'syn', '9', 'status', siliconcompiler.NodeStatus.ERROR)

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    # winner should be second-best, not syn9
    assert winner == ('syn', '8')


def test_winner_fails_goal_negative(chip):
    chip.set('metric', 'setupwns', -1, step='syn', index='9')

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    # winner should be second-best, not syn9
    assert winner == ('syn', '8')


def test_winner_fails_goal_positive(chip):
    flow = chip.get('option', 'flow')

    chip.set('flowgraph', flow, 'syn', '9', 'goal', 'errors', 0)
    chip.set('metric', 'errors', 1, step='syn', index='9')

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    # winner should be second-best, not syn9
    assert winner == ('syn', '8')


if __name__ == "__main__":
    test_minimum(chip())
