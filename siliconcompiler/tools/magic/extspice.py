from siliconcompiler.tools.magic.magic import setup as setup_tool
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''
    Extract spice netlists from a GDS file for simulation use
    '''

    # Generic tool setup
    setup_tool(chip)

    tool = 'magic'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'output', f'{design}.spice', step=step, index=index)
