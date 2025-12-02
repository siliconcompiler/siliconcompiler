from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADDPLParameter, \
    OpenROADCTSParameter


class CTSTask(APRTask, OpenROADSTAParameter, OpenROADDPLParameter, OpenROADCTSParameter):
    '''
    Perform clock tree synthesis
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "clock_tree_synthesis"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_clock_tree_synthesis.tcl")

        self._set_reports([
            'setup',
            'hold',
            'unconstrained',
            'clock_skew',
            'power',
            'drv_violations',
            'fmax',
            'report_buffers',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'optimization_placement',
            'clock_placement',
            'clock_trees',
            'module_view'
        ])
