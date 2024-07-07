
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners
from siliconcompiler.tools.openroad.openroad import post_process as or_post_process
from siliconcompiler.tools.openroad.openroad import pre_process as or_pre_process
from siliconcompiler.tools._common.asic import set_tool_task_var
from siliconcompiler.tools.openroad.openroad import _set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''
    Generate abstract views (LEF), timing libraries (liberty files),
    circuit descriptions (CDL), and parasitic annotation files (SPEF)
    '''

    # Generic tool setup.
    setup_tool(chip)

    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    tool = 'openroad'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Set thread count to 1 while issue related to write_timing_model segfaulting
    # when multiple threads are on is resolved.
    chip.set('tool', tool, 'task', task, 'threads', 1,
             step=step, index=index, clobber=True)

    stackup = chip.get('option', 'stackup')
    pdk = chip.get('option', 'pdk')

    targetlibs = chip.get('asic', 'logiclib', step=step, index=index)
    macrolibs = chip.get('asic', 'macrolib', step=step, index=index)

    # Determine if exporting the cdl
    set_tool_task_var(chip, param_key='write_cdl',
                      default_value='false',
                      schelp='true/false, when true enables writing the CDL file for the design')
    do_cdl = chip.get('tool', tool, 'task', task, 'var', 'write_cdl',
                      step=step, index=index)[0] == 'true'

    if do_cdl:
        chip.add('tool', tool, 'task', task, 'output', design + '.cdl', step=step, index=index)
        for lib in targetlibs + macrolibs:
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['library', lib, 'output', stackup, 'cdl']),
                     step=step, index=index)

    set_tool_task_var(chip, param_key='write_spef',
                      default_value='true',
                      schelp='true/false, when true enables writing the SPEF file for the design')
    do_spef = chip.get('tool', tool, 'task', task, 'var', 'write_spef',
                       step=step, index=index)[0] == 'true'
    set_tool_task_var(chip, param_key='use_spef',
                      default_value=do_spef,
                      schelp='true/false, when true enables reading in SPEF files.')

    if do_spef:
        # Require openrcx pex models
        for corner in chip.get('tool', tool, 'task', task, 'var', 'pex_corners',
                               step=step, index=index):
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['pdk', pdk, 'pexmodel', 'openroad-openrcx', stackup, corner]),
                     step=step, index=index)

        # Add outputs SPEF in the format {design}.{pexcorner}.spef
        for corner in chip.get('tool', tool, 'task', task, 'var', 'pex_corners',
                               step=step, index=index):
            chip.add('tool', tool, 'task', task, 'output', design + '.' + corner + '.spef',
                     step=step, index=index)

    # Add outputs LEF
    chip.add('tool', tool, 'task', task, 'output', design + '.lef', step=step, index=index)

    set_tool_task_var(chip, param_key='write_liberty',
                      default_value='true',
                      schelp='true/false, when true enables writing the liberty '
                             'timing model for the design')
    do_liberty = chip.get('tool', tool, 'task', task, 'var', 'write_liberty',
                          step=step, index=index)[0] == 'true'

    if do_liberty:
        # Add outputs liberty model in the format {design}.{libcorner}.lib
        for corner in chip.getkeys('constraint', 'timing'):
            chip.add('tool', tool, 'task', task, 'output', design + '.' + corner + '.lib',
                     step=step, index=index)

    set_tool_task_var(chip, param_key='write_sdf',
                      default_value='true',
                      schelp='true/false, when true enables writing the SDF timing model '
                             'for the design')
    do_sdf = chip.get('tool', tool, 'task', task, 'var', 'write_sdf',
                      step=step, index=index)[0] == 'true'
    if do_sdf:
        # Add outputs liberty model in the format {design}.{libcorner}.sdf
        for corner in chip.getkeys('constraint', 'timing'):
            chip.add('tool', tool, 'task', task, 'output', design + '.' + corner + '.sdf',
                     step=step, index=index)

    _set_reports(chip, [
        'setup',
        'hold',
        'unconstrained',
        'clock_skew',
        'power',
        'drv_violations',
        'fmax',

        # Images
        'placement_density',
        'routing_congestion',
        'power_density',
        'ir_drop',
        'clock_placement',
        'clock_trees',
        'optimization_placement'
    ])


def pre_process(chip):
    or_pre_process(chip)
    build_pex_corners(chip)


def post_process(chip):
    or_post_process(chip)
