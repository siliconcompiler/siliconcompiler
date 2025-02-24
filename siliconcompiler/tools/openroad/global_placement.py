from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs, \
    set_tool_task_var
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_gpl_params, define_grt_params, define_rsz_params, \
    define_ppl_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Perform global placement
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_global_placement.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_gpl_params(chip)
    define_grt_params(chip)
    define_rsz_params(chip)
    define_ppl_params(chip)

    set_reports(chip, [
        'setup',
        'unconstrained',
        'power',
        'fmax',

        # Images
        'placement_density',
        'routing_congestion',
        'power_density',
        'module_view'
    ])

    set_tool_task_var(chip, param_key='enable_multibit_clustering',
                      default_value=False,
                      schelp='true/false, when true multibit clustering will be performed.')

    set_tool_task_var(chip, param_key='enable_scan_chains',
                      default_value=False,
                      schelp='true/false, when true scan chains will be inserted.')

    set_tool_task_var(chip, param_key='scan_enable_port_pattern',
                      schelp='pattern of the scan chain enable port.',
                      skip=['pdk', 'lib'])
    set_tool_task_var(chip, param_key='scan_in_port_pattern',
                      schelp='pattern of the scan chain in port.',
                      skip=['pdk', 'lib'])
    set_tool_task_var(chip, param_key='scan_out_port_pattern',
                      schelp='pattern of the scan chain out port.',
                      skip=['pdk', 'lib'])


def pre_process(chip):
    define_ord_files(chip)
    build_pex_corners(chip)


def post_process(chip):
    extract_metrics(chip)
