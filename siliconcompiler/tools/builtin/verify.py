from siliconcompiler.tools.builtin import _common
from siliconcompiler.schema import Schema
from siliconcompiler.scheduler import _haltstep
from siliconcompiler.tools.builtin.builtin import set_io_files
from siliconcompiler import utils, flowgraph, SiliconCompilerError

import re


def setup(chip):
    '''
    Tests an assertion on an input task.

    The input to this task is verified to ensure that all assertions
    are True. If any of the assertions fail, False is returned.
    Assertions are passed in using ['flowgraph', flow, step, index, 'args'] in the form
    'metric==0.0'.
    The allowed conditional operators are: >, <, >=, <=, ==
    '''

    set_io_files(chip, outputs=False)


def _select_inputs(chip, step, index):
    inputs = _common._select_inputs(chip, step, index)
    if len(inputs) != 1:
        raise SiliconCompilerError(
            f'{step}{index} receives {len(inputs)} inputs, but only supports one', chip=chip)
    inputs = inputs[0]
    flow = chip.get('option', 'flow')
    arguments = chip.get('flowgraph', flow, step, index, 'args')

    if len(arguments) == 0:
        raise SiliconCompilerError(f'{step}{index} requires arguments for verify', chip=chip)

    passes = True
    for criteria in arguments:
        m = re.match(r'(\w+)([\>\=\<]+)(\w+)', criteria)
        if not m:
            raise SiliconCompilerError(f"Illegal verify criteria: {criteria}", chip=chip)

        metric = m.group(1)
        op = m.group(2)
        goal = m.group(3)
        if metric not in chip.getkeys('metric'):
            raise SiliconCompilerError(
                f"Criteria must use legal metrics only: {criteria}", chip=chip)

        value = chip.get('metric', metric, step=inputs[0], index=inputs[1])

        if value is None:
            raise SiliconCompilerError(
                f"Missing metric for {metric} in {inputs[0]}{inputs[1]}", chip=chip)

        metric_type = chip.get('metric', metric, field='type')
        goal = Schema._normalize_value(goal, metric_type, "", None)
        if not utils.safecompare(chip, value, op, goal):
            chip.error(f"{step}{index} fails '{metric}' metric: {value}{op}{goal}")

    if not passes:
        _haltstep(chip, flow, step, index)

    return inputs


def _gather_outputs(chip, step, index):
    flow = chip.get('option', 'flow')

    in_nodes = chip.get('flowgraph', flow, step, index, 'input')
    in_task_outputs = [flowgraph._gather_outputs(chip, *node) for node in in_nodes]

    if len(in_task_outputs) > 0:
        return in_task_outputs[0].intersection(*in_task_outputs[1:])

    return []


def run(chip):
    return _common.run(chip)


def post_process(chip):
    _common.post_process(chip)
