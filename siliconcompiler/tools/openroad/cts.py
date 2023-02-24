
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners, post_process

def setup(chip):
    '''
    Perform clock tree synthesis and timing repair
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    task = 'cts'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    chip.add('tool', tool, 'task', task, 'input', design +'.def', step=step, index=index)

def pre_process(chip):
    build_pex_corners(chip)
