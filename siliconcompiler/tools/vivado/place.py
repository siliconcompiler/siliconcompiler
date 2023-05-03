from siliconcompiler.tools import vivado
from siliconcompiler.tools.vivado import tool


def setup(chip):
    '''Performs placement.'''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    vivado.setup_task(chip, task)

    design = chip.top()
    chip.set('tool', tool, 'task', task, 'input', f'{design}_checkpoint.dcp',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', f'{design}_checkpoint.dcp',
             step=step, index=index)


def post_process(chip):
    vivado.post_process(chip)
