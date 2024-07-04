import os
from siliconcompiler.tools.opensta import setup as tool_setup
from siliconcompiler.tools.opensta import runtime_options as tool_runtime_options
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''
    Report information about the timing libraries.
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    tool_setup(chip)

    chip.set('tool', tool, 'task', task, 'script', 'sc_report_libraries.tcl',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index)


################################
# Runtime options
################################
def runtime_options(chip):
    return tool_runtime_options(chip)
