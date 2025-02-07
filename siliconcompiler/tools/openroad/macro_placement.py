from siliconcompiler import NodeStatus

from siliconcompiler.tools._common import has_pre_post_script, get_tool_task

from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_mpl_params, define_gpl_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Macro placement
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_macro_placement.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_mpl_params(chip)
    define_gpl_params(chip)

    set_reports(chip, [
        'setup',
        'unconstrained'
    ])

    chip.set('tool', tool, 'task', task, 'file', 'rtlmp_constraints',
             'contraints script for macro placement',
             field='help')

    if chip.get('tool', tool, 'task', task, 'file', 'rtlmp_constraints', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'file', 'rtlmp_constraints']),
                 step=step, index=index)


def pre_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    input_nodes = chip.get('record', 'inputnode', step=step, index=index)
    if not has_pre_post_script(chip) and all([
            chip.get('metric', 'macros', step=in_step, index=in_index) == 0
            for in_step, in_index in input_nodes
            ]):
        chip.set('record', 'status', NodeStatus.SKIPPED, step=step, index=index)
        chip.logger.warning(f'{step}{index} will be skipped since are no macros to place.')
        return

    build_pex_corners(chip)
    define_ord_files(chip)


def post_process(chip):
    extract_metrics(chip)
