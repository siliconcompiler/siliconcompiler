
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners
from siliconcompiler.tools.openroad.openroad import post_process as or_post_process
from siliconcompiler.tools.openroad.openroad import pre_process as or_pre_process


def setup(chip):
    '''
    Performs filler insertion, global routing, antenna repair, and detailed routing
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    chip.add('tool', tool, 'task', task, 'input', design + '.def', step=step, index=index)


def pre_process(chip):
    or_pre_process(chip)
    build_pex_corners(chip)


def post_process(chip):
    or_post_process(chip)
