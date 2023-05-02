
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners
from siliconcompiler.tools.openroad.openroad import post_process as or_post_process


def setup(chip):
    '''
    Generate abstract views (LEF), timing libraries (liberty files), circuit descriptions (CDL), and parasitic annotation files (SPEF)
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    stackup = chip.get('option', 'stackup')
    pdk = chip.get('option', 'pdk')

    targetlibs = chip.get('asic', 'logiclib', step=step, index=index)
    macrolibs = chip.get('asic', 'macrolib', step=step, index=index)

    # Determine if exporting the cdl
    chip.set('tool', tool, 'task', task, 'var', 'write_cdl', 'false', step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'write_cdl', 'true/false, when true enables writing the CDL file for the design', field='help')
    do_cdl = chip.get('tool', tool, 'task', task, 'var', 'write_cdl', step=step, index=index)[0] == 'true'

    if do_cdl:
        chip.add('tool', tool, 'task', task, 'output', design + '.cdl', step=step, index=index)
        for lib in targetlibs + macrolibs:
            chip.add('tool', tool, 'task', task, 'require', ",".join(['library', lib, 'output', stackup, 'cdl']), step=step, index=index)

    # Require openrcx pex models
    for corner in chip.get('tool', tool, 'task', task, 'var', 'pex_corners', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', ",".join(['pdk', pdk, 'pexmodel', 'openroad-openrcx', stackup, corner]), step=step, index=index)

    chip.add('tool', tool, 'task', task, 'input', design + '.def', step=step, index=index)

    # Add outputs LEF
    chip.add('tool', tool, 'task', task, 'output', design + '.lef', step=step, index=index)

    # Add outputs SPEF in the format {design}.{pexcorner}.spef
    for corner in chip.get('tool', tool, 'task', task, 'var', 'pex_corners', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'output', design + '.' + corner + '.spef', step=step, index=index)

    # Add outputs liberty model in the format {design}.{libcorner}.lib
    for corner in chip.get('tool', tool, 'task', task, 'var', 'timing_corners', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'output', design + '.' + corner + '.lib', step=step, index=index)


def pre_process(chip):
    build_pex_corners(chip)


def post_process(chip):
    or_post_process(chip)
