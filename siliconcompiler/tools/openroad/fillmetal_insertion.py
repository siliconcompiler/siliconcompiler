from siliconcompiler.tools._common import get_tool_task, has_pre_post_script
from siliconcompiler.tools._common.asic import get_mainlib

from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_fin_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Perform fill metal insertion
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_fillmetal_insertion.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_fin_params(chip)

    set_reports(chip, [
        'setup',
        'hold',
        'unconstrained',
        'clock_skew',
        'drv_violations',
        'fmax',

        # Images
        'placement_density',
        'routing_congestion',
        'power_density',
        'optimization_placement',
        'clock_placement',
        'clock_trees'
    ])

    if chip.get('tool', tool, 'task', task, 'var', 'fin_add_fill',
                step=step, index=index) == ["true"]:
        pdk = chip.get('option', 'pdk')
        stackup = chip.get('option', 'stackup')
        mainlib = get_mainlib(chip)
        libtype = chip.get('library', mainlib, 'asic', 'libarch', step=step, index=index)
        if chip.get('pdk', pdk, 'aprtech', tool, stackup, libtype, 'fill'):
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['pdk', pdk, 'aprtech', tool, stackup, libtype, 'fill']),
                     step=step, index=index)
        else:
            if not has_pre_post_script(chip):
                # nothing to do so we can skip
                return "no fill script is available"

            chip.set('tool', tool, 'task', task, 'var', 'fin_add_fill', False,
                     step=step, index=index)


def pre_process(chip):
    define_ord_files(chip)
    build_pex_corners(chip)


def post_process(chip):
    extract_metrics(chip)
