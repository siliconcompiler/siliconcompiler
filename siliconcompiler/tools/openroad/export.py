
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners

def setup(chip):
    ''' Helper method for configs specific to export tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    task = 'export'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    stackup = chip.get('option', 'stackup')
    pdk = chip.get('option', 'pdk')

    targetlibs = chip.get('asic', 'logiclib')
    macrolibs = chip.get('asic', 'macrolib')

    # Determine if exporting the cdl
    chip.set('tool', tool, 'task', task, 'var', step, index, 'write_cdl', 'true', clobber=False)
    do_cdl = chip.get('tool', tool, 'task', task, 'var', step, index, 'write_cdl')[0] == 'true'

    if do_cdl:
        chip.add('tool', tool, 'task', task, 'output', step, index, design + '.cdl')
        for lib in targetlibs + macrolibs:
            chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'cdl']))

    # Require openrcx pex models
    for corner in chip.get('tool', tool, 'task', task, 'var', step, index, 'pex_corners'):
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['pdk', pdk, 'pexmodel', 'openroad-openrcx', stackup, corner]))

    chip.add('tool', tool, 'task', task, 'input', step, index, design +'.def')

    # Add outputs LEF
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.lef')

    # Add outputs SPEF in the format {design}.{pexcorner}.spef
    for corner in chip.get('tool', tool, 'task', task, 'var', step, index, 'pex_corners'):
        chip.add('tool', tool, 'task', task, 'output', step, index, design + '.' + corner + '.spef')

    # Add outputs liberty model in the format {design}.{libcorner}.lib
    for corner in chip.get('tool', tool, 'task', task, 'var', step, index, 'timing_corners'):
        chip.add('tool', tool, 'task', task, 'output', step, index, design + '.' + corner + '.lib')

def pre_process(chip):
    build_pex_corners(chip)
