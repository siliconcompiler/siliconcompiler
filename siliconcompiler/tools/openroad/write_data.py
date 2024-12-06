from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.tools._common.asic import get_libraries, set_tool_task_var
from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_pex_params, define_psm_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Write output files
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_write_data.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_pex_params(chip)
    define_psm_params(chip)

    pdkname = chip.get('option', 'pdk')
    targetlibs = get_libraries(chip, 'logic')
    macrolibs = get_libraries(chip, 'macro')
    stackup = chip.get('option', 'stackup')

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
                     ",".join(['pdk', pdkname, 'pexmodel', 'openroad-openrcx', stackup, corner]),
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

    set_reports(chip, [
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
    define_ord_files(chip)
    build_pex_corners(chip)


def post_process(chip):
    extract_metrics(chip)
