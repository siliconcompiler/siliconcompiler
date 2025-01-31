from siliconcompiler.tools._common import input_provides, add_common_file, get_tool_task
from siliconcompiler.tools._common.asic import set_tool_task_var, get_mainlib

from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_tiecell_params, define_pad_params, define_ppl_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Perform floorplanning and initial pin placements
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_init_floorplan.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)
    add_common_file(chip, 'sc_pin_constraint', 'tcl/sc_pin_constraints.tcl')

    # set default values for task
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_pad_params(chip)
    define_ppl_params(chip)
    define_tiecell_params(chip)

    set_tool_task_var(chip, param_key='ifp_snap_strategy',
                      default_value='site',
                      schelp='Snapping strategy to use when placing macros. '
                             'Allowed values: none, site, manufacturing_grid')

    set_tool_task_var(chip, param_key='remove_synth_buffers',
                      default_value=True,
                      schelp='remove buffers inserted by synthesis')

    set_tool_task_var(chip, param_key='remove_dead_logic',
                      default_value=True,
                      schelp='remove logic which does not drive a primary output')

    # Handle additional input files
    if chip.valid('input', 'asic', 'floorplan') and \
       chip.get('input', 'asic', 'floorplan', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['input', 'asic', 'floorplan']),
                 step=step, index=index)

    if f'{design}.vg' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', f'{design}.vg',
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require', 'input,netlist,verilog',
                 step=step, index=index)

    set_reports(chip, [
        'check_setup',
        'setup',
        'unconstrained',
        'power'
    ])

    mainlib = get_mainlib(chip)

    # Setup required
    for component in chip.getkeys('constraint', 'component'):
        for key in chip.getkeys('constraint', 'component', component):
            if chip.get('constraint', 'component', component, key, step=step, index=index):
                chip.add('tool', tool, 'task', task, 'require',
                         ','.join(['constraint', 'component', component, key]),
                         step=step, index=index)
    for pin in chip.getkeys('constraint', 'pin'):
        for key in chip.getkeys('constraint', 'pin', pin):
            if chip.get('constraint', 'pin', pin, key, step=step, index=index):
                chip.add('tool', tool, 'task', task, 'require',
                         ','.join(['constraint', 'pin', pin, key]),
                         step=step, index=index)
    for ifp in ('aspectratio', 'density', 'corearea', 'coremargin', 'outline'):
        if chip.get('constraint', ifp, step=step, index=index):
            chip.add('tool', tool, 'task', task, 'require',
                     ','.join(['constraint', ifp]),
                     step=step, index=index)
    if chip.valid('library', mainlib, 'option', 'file', 'openroad_tracks'):
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['library', mainlib, 'option', 'file', 'openroad_tracks']),
                 step=step, index=index)


def pre_process(chip):
    build_pex_corners(chip)
    define_ord_files(chip)


def post_process(chip):
    extract_metrics(chip)
