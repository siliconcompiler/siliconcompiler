from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADGRTParameter, \
    OpenROADDRTPinAccessParameter


class GlobalRouteTask(APRTask, OpenROADSTAParameter, OpenROADGRTParameter,
                      OpenROADDRTPinAccessParameter):
    '''
    Perform global routing
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("grt_use_pin_access", "bool",
                           "true/false, when true perform pin access before global routing",
                           defvalue=False)

    def task(self):
        return "global_route"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_global_route.tcl")

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

        self.add_required_key("var", "grt_use_pin_access")
