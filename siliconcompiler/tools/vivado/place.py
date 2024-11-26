from siliconcompiler.tools import vivado
from siliconcompiler.tools.vivado import tool
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''Performs placement.'''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    vivado.setup_task(chip, task)

    design = chip.top()
    chip.set('tool', tool, 'task', task, 'input', f'{design}.dcp',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', f'{design}.dcp',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.xdc',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.vg',
             step=step, index=index)


def post_process(chip):
    vivado.post_process(chip)
