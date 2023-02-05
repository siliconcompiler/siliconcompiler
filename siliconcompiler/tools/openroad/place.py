
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners, post_process

def setup(chip):
    ''' Helper method for configs specific to place tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    task = 'place'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if (not chip.valid('input', 'layout', 'def') or
        not chip.get('input', 'layout', 'def')):
        chip.add('tool', tool, 'task', task, 'input', step, index, design +'.def')

def pre_process(chip):
    build_pex_corners(chip)
