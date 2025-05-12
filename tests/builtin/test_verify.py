# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import pytest

from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic

from siliconcompiler.tools.builtin import verify


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
        'teststep': verify
    }

    flow = 'testflow'
    chip.set('option', 'flow', flow)

    for i, step in enumerate(flowpipe):
        if step == "teststep":
            chip.node(flow, step, task[step])
            chip.edge(flow, flowpipe[i - 1], step)
        elif step == 'import':
            chip.node(flow, step, task[step])
        else:
            chip.node(flow, step, task[step])
            chip.edge(flow, flowpipe[i - 1], step)

    # creating fake syn results
    for metric in chip.getkeys('metric'):
        if metric != 'setuptns':
            chip.set('metric', metric, 1000 + 42.0, step='syn', index='0')

    return chip


##################################
def test_verify_pass(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'errors==1042')

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner == ('syn', '0')


##################################
def test_verify_pass_greater(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'errors>=0')

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner == ('syn', '0')


##################################
def test_verify_fail(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'errors==1041')

    task = chip._get_task_module('teststep', '0')
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        task._select_inputs(chip, 'teststep', '0')


##################################
def test_verify_pass_two_metrics(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'errors==1042')
    chip.add('flowgraph', flow, 'teststep', '0', 'args', 'warnings==1042')

    task = chip._get_task_module('teststep', '0')
    winner = task._select_inputs(chip, 'teststep', '0')

    assert winner == ('syn', '0')


##################################
def test_verify_partial_fail(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'errors==1042')
    chip.add('flowgraph', flow, 'teststep', '0', 'args', 'warnings==1041')

    task = chip._get_task_module('teststep', '0')
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        task._select_inputs(chip, 'teststep', '0')


##################################
def test_verify_partial_missing(chip):
    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'teststep', '0', 'args', 'errors==1042')
    chip.add('flowgraph', flow, 'teststep', '0', 'args', 'setuptns>=0')

    task = chip._get_task_module('teststep', '0')
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        task._select_inputs(chip, 'teststep', '0')
