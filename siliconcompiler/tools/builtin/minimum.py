from siliconcompiler.tools.builtin import _common
from siliconcompiler.tools.builtin.builtin import set_io_files
from siliconcompiler.tools._common import get_tool_task


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

    set_io_files(chip)


def _select_inputs(chip, step, index):
    inputs = _common._select_inputs(chip, step, index)

    score, sel_inputs = _common._minmax(chip, *inputs, op='minimum')

    if sel_inputs:
        chip.logger.info(f"Selected '{sel_inputs[0]}{sel_inputs[1]}' with score {score:.3f}")

    return sel_inputs


def _gather_outputs(chip, step, index):
    '''Return set of filenames that are guaranteed to be in outputs
    directory after a successful run of step/index.'''

    flow = chip.get('option', 'flow')

    in_nodes = chip.get('flowgraph', flow, step, index, 'input')
    in_task_outputs = []
    for in_step, in_index in in_nodes:
        in_tool, _ = get_tool_task(chip, in_step, in_index, flow=flow)
        task_class = chip.get("tool", in_tool, field="schema")
        task_class.set_runtime(chip, step=in_step, index=in_index)
        in_task_outputs.append(task_class.get_output_files())

    if len(in_task_outputs) > 0:
        return in_task_outputs[0].intersection(*in_task_outputs[1:])

    return []


def run(chip):
    return _common.run(chip)


def post_process(chip):
    _common.post_process(chip)
