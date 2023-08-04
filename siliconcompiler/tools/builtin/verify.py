from siliconcompiler.tools.builtin import _common
from siliconcompiler.schema import Schema

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


def _select_inputs(chip, step, index):
    chip.logger.info("Running builtin task 'verify'")

    flow = chip.get('option', 'flow')
    inputs = chip.get('flowgraph', flow, step, index, 'input')
    if len(inputs) != 1:
        chip.error(f'{step}{index} receives {len(inputs)} inputs, but only supports 1', fatal=True)
    inputs = inputs[0]
    arguments = chip.get('flowgraph', flow, step, index, 'args')

    if len(arguments) == 0:
        chip.error(f'{step}{index} requires arguments for verify', fatal=True)

    passes = True
    for criteria in arguments:
        m = re.match(r'(\w+)([\>\=\<]+)(\w+)', criteria)
        if not m:
            chip.error(f"Illegal verify criteria: {criteria}", fatal=True)

        metric = m.group(1)
        op = m.group(2)
        goal = m.group(3)
        if metric not in chip.getkeys('metric'):
            chip.error(f"Criteria must use legal metrics only: {criteria}", fatal=True)

        value = chip.get('metric', metric, step=inputs[0], index=inputs[1])

        if value is None:
            chip.error(f"Missing metric for {metric} in {inputs[0]}{inputs[1]}", fatal=True)

        metric_type = chip.get('metric', metric, field='type')
        goal = Schema._normalize_value(goal, metric_type, "", None)
        if not chip._safecompare(value, op, goal):
            chip.error(f"{step}{index} fails '{metric}' metric: {value}{op}{goal}")

    if not passes:
        chip._haltstep(step, index)

    return inputs


def _gather_outputs(chip, step, index):
    flow = chip.get('option', 'flow')

    in_nodes = chip.get('flowgraph', flow, step, index, 'input')
    in_task_outputs = [chip._gather_outputs(*node) for node in in_nodes]

    if len(in_task_outputs) > 0:
        return in_task_outputs[0].intersection(*in_task_outputs[1:])

    return []


def run(chip):
    return _common.run(chip)


def post_process(chip):
    _common.post_process(chip)
