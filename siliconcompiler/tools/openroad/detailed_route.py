from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, \
    OpenROADDRTPinAccessParameter, OpenROADDRTParameter


class DetailedRouteTask(APRTask, OpenROADSTAParameter, OpenROADDRTPinAccessParameter,
                        OpenROADDRTParameter):
    '''
    Perform detailed routing
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "detailed_route"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_detailed_route.tcl")

        self._set_reports([
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
