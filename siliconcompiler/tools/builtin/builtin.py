from siliconcompiler.tools._common import input_provides
'''
Builtin tools for SiliconCompiler
'''


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    return chip


def set_io_files(chip, inputs=True, outputs=True):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    if inputs:
        chip.set('tool', tool, 'task', task, 'input',
                 list(input_provides(chip, step, index).keys()),
                 step=step, index=index)
    if outputs:
        chip.set('tool', tool, 'task', task, 'output',
                 list(input_provides(chip, step, index).keys()),
                 step=step, index=index)
