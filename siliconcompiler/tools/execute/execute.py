'''
This tool is used to execute the output of a previous step.
For example, if the flow contains a compile step which generates the
next executable needed in the flow.
'''

from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'exe', ":exe:", clobber=False)
    chip.set('tool', tool, 'task', task, 'option', [], step=step, index=index, clobber=False)
