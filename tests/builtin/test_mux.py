# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import pytest

from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic

from siliconcompiler.tools.builtin import mux


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
        'teststep': mux
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

    # creating fake syn results
    for index in range(N):
        for metric in chip.getkeys('metric'):
            if metric != 'setupwns':
                chip.set('metric', metric, 1000 - index * 1 + 42.0, step='syn', index=index)
            else:
                chip.set('metric', metric, index % 3, step='syn', index=index)

    return chip


##################################
def test_minimum(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'minimum(setuptns)')

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner == ('syn', '9')


def test_maximum(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'maximum(setuptns)')

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner == ('syn', '0')


def test_minimum_two_metrics(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'maximum(setupwns)')
    chip.add('flowgraph', flow, 'teststep', '0', 'args', 'minimum(setuptns)')

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner == ('syn', '8')
