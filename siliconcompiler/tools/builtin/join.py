from siliconcompiler.tools.builtin import _common
from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin.builtin import set_io_files

from siliconcompiler.tools.builtin import BuiltinTask


class JoinTask(BuiltinTask):
    def __init__(self):
        super().__init__()

    def task(self):
        return "join"


def setup(chip):
    '''
    Merges outputs from a list of input tasks.
    '''

    set_io_files(chip)


def _select_inputs(chip, step, index):
    return _common._select_inputs(chip, step, index)


def _gather_outputs(chip, step, index):
    return nop._gather_outputs(chip, step, index)


def run(chip):
    return _common.run(chip)


def post_process(chip):
    _common.post_process(chip)
