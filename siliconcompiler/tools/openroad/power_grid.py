from siliconcompiler import NodeStatus

from siliconcompiler.tools._common import get_tool_task, has_pre_post_script
from siliconcompiler.tools._common.asic import set_tool_task_var

from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_pdn_params, define_psm_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, \
    define_ord_files, define_pdn_files
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Perform power grid insertion and connectivity analysis
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_power_grid.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_pdn_params(chip)
    define_psm_params(chip)

    set_tool_task_var(chip, param_key='fixed_pin_keepout',
                      default_value=0,
                      schelp='if > 0, applies a blockage in multiples of the routing pitch '
                             'to each fixed pin to ensure there is room for routing.')

    set_reports(chip, [])


def pre_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    define_pdn_files(chip)
    pdncfg = [file for file in chip.find_files('tool', tool, 'task', task, 'file', 'pdn_config',
                                               step=step, index=index) if file]
    if not has_pre_post_script(chip) and \
            (chip.get('tool', tool, 'task', task, 'var', 'pdn_enable',
                      step=step, index=index)[0] == 'false' or len(pdncfg) == 0):
        chip.set('record', 'status', NodeStatus.SKIPPED, step=step, index=index)
        chip.logger.warning(f'{step}{index} will be skipped since power grid is disabled.')
        return

    define_ord_files(chip)
    build_pex_corners(chip)


def post_process(chip):
    extract_metrics(chip)
