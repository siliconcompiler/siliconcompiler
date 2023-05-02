
from siliconcompiler.tools.magic.magic import setup as setup_tool


def setup(chip):
    '''
    Extract spice netlists from a GDS file for simulation use
    '''

    # Generic tool setup
    setup_tool(chip)

    tool = 'magic'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'output', f'{design}.spice', step=step, index=index)
