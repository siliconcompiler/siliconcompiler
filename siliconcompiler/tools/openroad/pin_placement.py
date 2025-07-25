from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_gpl_params, define_ppl_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools.openroad._apr import extract_metrics


from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADGPLParameter, OpenROADPPLParameter


class PinPlacementTask(APRTask, OpenROADSTAParameter, OpenROADGPLParameter, OpenROADPPLParameter):
    def __init__(self):
        super().__init__()

    def task(self):
        return "pin_placement"

    def setup(self):
        super().setup()

        self.set("script", "apr/sc_pin_placement.tcl")

        self._set_reports([
            'setup',
            'unconstrained',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'module_view'
        ])


def setup(chip):
    '''
    Perform IO pin placement refinement
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_pin_placement.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_gpl_params(chip)
    define_ppl_params(chip)

    set_reports(chip, [
        'setup',
        'unconstrained',

        # Images
        'placement_density',
        'routing_congestion',
        'power_density',
        'module_view'
    ])


def pre_process(chip):
    define_ord_files(chip)
    build_pex_corners(chip)


def post_process(chip):
    extract_metrics(chip)
