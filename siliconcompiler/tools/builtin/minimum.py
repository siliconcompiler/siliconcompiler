from siliconcompiler.tools.builtin import _common


def setup(chip):
    '''
    Selects the task with the minimum metric score from a list of inputs.

    Sequence of operation:

    1. Check list of input tasks to see if all metrics meets goals
    2. Check list of input tasks to find global min/max for each metric
    3. Select MIN value if all metrics are met.
    4. Normalize the min value as sel = (val - MIN) / (MAX - MIN)
    5. Return normalized value and task name

    Meeting metric goals takes precedence over compute metric scores.
    Only goals with values set and metrics with weights set are considered
    in the calculation.
    '''
    pass


def _select_inputs(chip, step, index):
    chip.logger.info("Running builtin task 'minimum'")

    flow = chip.get('option', 'flow')
    inputs = chip._get_pruned_node_inputs(flow, (step, index))

    score, sel_inputs = _common._minmax(chip, *inputs, op='minimum')

    if sel_inputs:
        chip.logger.info(f"Selected '{sel_inputs[0]}{sel_inputs[1]}' with score {score:.3f}")

    return sel_inputs


def _gather_outputs(chip, step, index):
    '''Return set of filenames that are guaranteed to be in outputs
    directory after a successful run of step/index.'''

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
