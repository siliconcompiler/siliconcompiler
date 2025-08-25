from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADDPLParameter, \
    OpenROADFillCellsParameter


class FillCellTask(APRTask, OpenROADSTAParameter, OpenROADDPLParameter, OpenROADFillCellsParameter):
    '''
    Perform filler cell insertion
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "fillercell_insertion"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_fillercell_insertion.tcl")

        self._set_reports([
            'setup',
            'hold',
            'unconstrained',
            'power',
            'drv_violations',
            'fmax',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'module_view'
        ])
