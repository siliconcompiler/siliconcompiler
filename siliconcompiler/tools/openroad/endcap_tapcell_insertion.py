from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_tapcell_params, define_tiecell_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, \
    define_ord_files, define_tapcell_files
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Perform endcap and tap cell insertion
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_endcap_tapcell_insertion.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_tapcell_params(chip)
    define_tiecell_params(chip)

    set_reports(chip, [
        # Images
        'placement_density'
    ])


def pre_process(chip):
    define_ord_files(chip)
    define_tapcell_files(chip)
    build_pex_corners(chip)


def post_process(chip):
    extract_metrics(chip)
