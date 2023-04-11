from siliconcompiler.tools.builtin import _common
import re

def setup(chip):
    '''
    Selects a task from a list of inputs.

    The selector criteria provided is used to create a custom function
    for selecting the best step/index pair from the inputs. Metrics and
    weights are passed in and used to select the step/index based on
    the minimum or maximum score depending on the 'op' argument.

    The function can be used to bypass the flows weight functions for
    the purpose of conditional flow execution and verification.
    '''
    pass

def _select_inputs(chip, step, index):
    chip.logger.info(f"Running builtin task 'mux'")
    
    flow = chip.get('option', 'flow')
    inputs = chip.get('flowgraph', flow, step, index, 'input')
    arguments = chip.get('flowgraph', flow, step, index, 'args')

    if len(arguments) != 1:
        chip.error(f'{step}{index} has {len(arguments)} arguments, but only support 1.', fatal=True)
    criteria = arguments[0]

    m = re.match(r'(\w+)([\>\=\<]+)(\w+)', criteria)
    if not m:
        chip.error(f"Illegal checklist criteria: {criteria}", fatal=True)

    metric = m.group(1)
    op = m.group(2)
    if metric not in chip.getkeys('metric'):
        chip.error(f"Critera must use legal metrics only: {criteria}", fatal=True)

    operation = 'minimum'
    if op == '>=' or op == '>':
        operation = 'maximum'

    score, sel_inputs = _common._mux(chip, *inputs, op=operation, metric=metric)

    if sel_inputs:
        chip.logger.info(f"Selected '{sel_inputs[0]}{sel_inputs[1]}' with score {score:.3f}")

    return sel_inputs

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
