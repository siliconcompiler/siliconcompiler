
from .magic import setup as setup_tool

def setup(chip):
    ''' Helper method to setup configs specific to extspice tasks.
    '''

    # Generic tool setup
    setup_tool(chip)

    tool = 'magic'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'extspice'
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'output', step, index, f'{design}.spice')
