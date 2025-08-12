from siliconcompiler.tools.builtin import _common
from siliconcompiler.tools.builtin.builtin import set_io_files
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.builtin import BuiltinTask


class NOPTask(BuiltinTask):
    '''
    A no-operation that passes inputs to outputs.
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "nop"
