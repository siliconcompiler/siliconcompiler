from siliconcompiler.tools import vivado
from siliconcompiler.tools.vivado import tool

def setup(chip):
    '''Generates bitstream of implemented design.'''
    task = 'bitstream'
    vivado.setup_task(chip, task)

    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'step')
    chip.set('tool', tool, 'task', task, 'input', f'{design}_checkpoint.dcp', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', f'{design}.bit', step=step, index=index)

def post_process(chip):
    vivado.post_process(chip)
