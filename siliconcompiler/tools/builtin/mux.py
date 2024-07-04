from siliconcompiler.tools.builtin import _common
import re
from siliconcompiler.tools.builtin.builtin import set_io_files
from siliconcompiler import flowgraph, SiliconCompilerError


def setup(chip):
    '''
    Selects a task from a list of inputs.

    The selector criteria provided is used to create a custom function
    for selecting the best step/index pair from the inputs. Metrics and
    weights are passed in and used to select the step/index based on
    the minimum or maximum score depending on the 'op' argument from
    ['flowgraph', flow, step, index, 'args'] in the form 'minimum(metric)' or
    'maximum(metric)'.

    The function can be used to bypass the flows weight functions for
    the purpose of conditional flow execution and verification.
    '''

    set_io_files(chip)


def _select_inputs(chip, step, index):
    chip.logger.info("Running builtin task 'mux'")

    flow = chip.get('option', 'flow')
    inputs = chip.get('flowgraph', flow, step, index, 'input')
    arguments = chip.get('flowgraph', flow, step, index, 'args')

    operations = []
    for criteria in arguments:
        m = re.match(r'(minimum|maximum)\((\w+)\)', criteria)
        if not m:
            raise SiliconCompilerError(f"Illegal mux criteria: {criteria}", chip=chip)

        op = m.group(1)
        metric = m.group(2)
        if metric not in chip.getkeys('metric'):
            raise SiliconCompilerError(
                f"Criteria must use legal metrics only: {criteria}", chip=chip)

        operations.append((metric, op))
    score, sel_inputs = _common._mux(chip, *inputs, operations=operations)

    if sel_inputs:
        chip.logger.info(f"Selected '{sel_inputs[0]}{sel_inputs[1]}' with score {score:.3f}")

    return sel_inputs


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
