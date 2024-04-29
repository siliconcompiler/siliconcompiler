
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import post_process as or_post_process
from siliconcompiler.tools.openroad.openroad import pre_process as or_pre_process


def setup(chip):
    '''
    Perform post-synthesis static timing analysis (STA)
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    if not chip.valid('input', 'netlist', 'verilog') or \
       not chip.get('input', 'netlist', 'verilog', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'input', design + '.vg', step=step, index=index)

def pre_process(chip):
    or_pre_process(chip)


def post_process(chip):
    or_post_process(chip)
