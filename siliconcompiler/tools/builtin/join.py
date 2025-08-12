from siliconcompiler.tools.builtin import _common
from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin.builtin import set_io_files

from siliconcompiler.tools.builtin import BuiltinTask


class JoinTask(BuiltinTask):
    '''
    Merges outputs from a list of input tasks.
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "join"
