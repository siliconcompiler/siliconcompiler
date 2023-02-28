
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners, post_process

def setup(chip):
    '''
    Perform floorplanning, pin placements, macro placements and power grid generation
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    task = 'floorplan'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if chip.valid('input', 'asic', 'floorplan'):
        chip.add('tool', tool, 'task', task, 'require', ",".join(['input', 'asic', 'floorplan']), step=step, index=index)

    if (not chip.valid('input', 'netlist', 'verilog') or
        not chip.get('input', 'netlist', 'verilog', step=step, index=index)):
        chip.add('tool', tool, 'task', task, 'input', design +'.vg', step=step, index=index)

    if chip.valid('tool', tool, 'task', task, 'file', 'padring'):
        chip.add('tool', tool, 'task', task, 'require', ','.join(['tool', tool, 'task', task, 'file', 'padring']))
    chip.set('tool', tool, 'task', task, 'file', 'padring', 'script to insert the padring', field='help')

def pre_process(chip):
    build_pex_corners(chip)
