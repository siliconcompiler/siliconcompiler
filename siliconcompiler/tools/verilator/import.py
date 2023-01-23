
from .verilator import setup as setup_tool

def setup(chip):
    ''' Helper method to load configs specific to compile tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'verilator'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'import'
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'option', step, index,  ['--lint-only', '--debug'])
    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['input', 'rtl', 'verilog']))
    chip.add('tool', tool, 'task', task, 'output', step, index, f'{design}.v')
    for value in chip.get('option', 'define'):
        chip.add('tool', tool, 'task', task, 'option', step, index, '-D' + value)
