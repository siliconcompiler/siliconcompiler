
from .openroad import setup as setup_tool

def setup(chip):
    ''' Helper method for configs specific to floorplan tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    task = 'floorplan'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if (not chip.valid('input', 'netlist', 'verilog') or
        not chip.get('input', 'netlist', 'verilog')):
        chip.add('tool', tool, 'task', task, 'input', step, index, design +'.vg')
