
from siliconcompiler.tools.verilator.verilator import setup as setup_tool

def setup(chip):
    ''' Helper method to load configs specific to compile tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'verilator'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'lint'
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'option',  ['--lint-only', '--debug'], step=step, index=index)
    chip.set('tool', tool, 'task', task, 'input', f'inputs/{design}.v', step=step, index=index)
