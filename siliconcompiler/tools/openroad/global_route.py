from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_grt_params, define_drt_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Perform global routing
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_grt_params(chip, load_all=True)
    define_drt_params(chip)

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
        'optimization_placement',
        'clock_placement',
        'clock_trees'
    ])


def pre_process(chip):
    define_ord_files(chip)
    build_pex_corners(chip)


def post_process(chip):
    extract_metrics(chip)
