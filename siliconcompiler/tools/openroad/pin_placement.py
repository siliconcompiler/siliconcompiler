from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADGPLParameter, \
    OpenROADPPLParameter


class PinPlacementTask(APRTask, OpenROADSTAParameter, OpenROADGPLParameter, OpenROADPPLParameter):
    '''
    Perform IO pin placement refinement
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "pin_placement"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_pin_placement.tcl")

        self._set_reports([
            'setup',
            'unconstrained',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'module_view'
        ])
