from siliconcompiler.tools.builtin import _common
from siliconcompiler.tools.builtin.builtin import set_io_files
from siliconcompiler import flowgraph


def setup(chip):
    '''
    A no-operation that passes inputs to outputs.
    '''

    set_io_files(chip)


def _select_inputs(chip, step, index):
    return _common._select_inputs(chip, step, index)


def _gather_outputs(chip, step, index):
    '''Return set of filenames that are guaranteed to be in outputs
    directory after a successful run of step/index.'''

    flow = chip.get('option', 'flow')

    in_nodes = chip.get('flowgraph', flow, step, index, 'input')
    in_task_outputs = [flowgraph._gather_outputs(chip, *node) for node in in_nodes]

    if len(in_task_outputs) > 0:
        return in_task_outputs[0].union(*in_task_outputs[1:])

    return []


def run(chip):
    return _common.run(chip)


def post_process(chip):
    _common.post_process(chip)
