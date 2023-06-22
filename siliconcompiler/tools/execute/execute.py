'''
This tool is used to execute the output of a previous step.
For example, if the flow contains a compile step which generates the
next executable needed in the flow.
'''


def setup(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    tool, task = chip._get_tool_task(step, index)

    chip.set('tool', tool, 'exe', ":exe:", clobber=False)
    chip.set('tool', tool, 'task', task, 'option', [], step=step, index=index, clobber=False)
