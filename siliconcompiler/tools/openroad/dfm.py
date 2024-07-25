
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners
from siliconcompiler.tools.openroad.openroad import post_process as or_post_process
from siliconcompiler.tools.openroad.openroad import pre_process as or_pre_process
from siliconcompiler.tools.openroad.openroad import _set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.tools._common.asic import get_mainlib
from siliconcompiler import NodeStatus


def setup(chip):
    '''
    Design for manufacturing step will insert fill if specified
    '''

    # Generic tool setup.
    setup_tool(chip)

    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

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
        'clock_placement',
        'clock_trees',
        'optimization_placement'
    ])


def pre_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    if not chip.find_files('tool', tool, 'task', task, 'prescript',
                           step=step, index=index) and \
            not chip.find_files('tool', tool, 'task', task, 'postscript',
                                step=step, index=index) and \
            chip.get('tool', tool, 'task', task, 'var', 'fin_add_fill',
                     step=step, index=index) == ["true"]:
        pdk = chip.get('option', 'pdk')
        stackup = chip.get('option', 'stackup')
        mainlib = get_mainlib(chip)
        libtype = chip.get('library', mainlib, 'asic', 'libarch', step=step, index=index)

        if not chip.find_files('pdk', pdk, 'aprtech', tool, stackup, libtype, 'fill'):
            chip.set('record', 'status', NodeStatus.SKIPPED, step=step, index=index)
            chip.logger.warning(f'{step}{index} will be skipped since there is nothing to do.')

    or_pre_process(chip)
    build_pex_corners(chip)


def post_process(chip):
    or_post_process(chip)
