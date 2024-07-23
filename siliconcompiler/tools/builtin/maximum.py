from siliconcompiler.tools.builtin import _common
from siliconcompiler.tools.builtin import minimum
from siliconcompiler.tools.builtin.builtin import set_io_files


def setup(chip):
    '''
    Selects the task with the maximum metric score from a list of inputs.

    Sequence of operation:

    1. Check list of input tasks to see if all metrics meets goals
    2. Check list of input tasks to find global min/max for each metric
    3. Select MAX value if all metrics are met.
    4. Normalize the min value as sel = (val - MIN) / (MAX - MIN)
    5. Return normalized value and task name

    Meeting metric goals takes precedence over compute metric scores.
    Only goals with values set and metrics with weights set are considered
    in the calculation.
    '''

    set_io_files(chip)


def _select_inputs(chip, step, index):
    inputs = _common._select_inputs(chip, step, index)

    score, sel_inputs = _common._minmax(chip, *inputs, op='maximum')

    if sel_inputs:
        chip.logger.info(f"Selected '{sel_inputs[0]}{sel_inputs[1]}' with score {score:.3f}")

    return sel_inputs


def _gather_outputs(chip, step, index):
    return minimum._gather_outputs(chip, step, index)


def run(chip):
    return _common.run(chip)


def post_process(chip):
    _common.post_process(chip)
