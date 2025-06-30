from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADDPLParameter, \
    OpenROADDPOParameter


class DetailedPlacementTask(APRTask, OpenROADSTAParameter, OpenROADDPLParameter,
                            OpenROADDPOParameter):
    '''
    Perform detailed placement
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "detailed_placement"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_detailed_placement.tcl")

        self._set_reports([
            'setup',
            'unconstrained',
            'power',
            'drv_violations',
            'fmax',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'optimization_placement',
            'module_view'
        ])
