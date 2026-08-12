from siliconcompiler import TaskSkip
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADGRTParameter, \
    OpenROADANTParameter, OpenROADFillCellsParameter


class AntennaRepairTask(APRTask, OpenROADSTAParameter, OpenROADGRTParameter, OpenROADANTParameter,
                        OpenROADFillCellsParameter):
    '''
    Perform antenna repair
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "antenna_repair"

    def setup(self):
        # ant_check cannot change between setup and execution, so drop the node here
        # rather than in pre_process and avoid building a work directory for it.
        if not self.get("var", "ant_check"):
            raise TaskSkip("antenna repair is disabled")

        super().setup()

        self.set_script("apr/sc_antenna_repair.tcl")

        self._set_reports([
            'scenarios',
            'setup',
            'hold',
            'unconstrained',
            'clock_skew',
            'power',
            'drv_violations',
            'fmax',
            'floating_nets',
            'overdriven_nets',
            "logicdepth",

            # Images
            'snapshot',
            'placement_view',
            'routing_view',
            'markers_view',
            'placement_density',
            'routing_congestion',
            'power_density',
            'optimization_placement',
            'clock_placement',
            'clock_trees',
            'module_view'
        ])
