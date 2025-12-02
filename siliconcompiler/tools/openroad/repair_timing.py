from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADDPLParameter, \
    OpenROADRSZDRVParameter, OpenROADRSZTimingParameter, OpenROADFillCellsParameter


class RepairTimingTask(APRTask, OpenROADSTAParameter, OpenROADDPLParameter,
                       OpenROADRSZDRVParameter, OpenROADRSZTimingParameter,
                       OpenROADFillCellsParameter):
    '''
    Perform setup and hold timing repairs
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("rsz_skip_drv_repair", "bool", "skip design rule violation repair",
                           defvalue=False)
        self.add_parameter("rsz_skip_setup_repair", "bool", "skip setup timing repair",
                           defvalue=False)
        self.add_parameter("rsz_skip_hold_repair", "bool", "skip hold timing repair",
                           defvalue=False)
        self.add_parameter("rsz_skip_recover_power", "bool", "skip power recovery",
                           defvalue=False)

    def task(self):
        return "repair_timing"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_repair_timing.tcl")

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

        self.add_required_key("var", "rsz_skip_drv_repair")
        self.add_required_key("var", "rsz_skip_setup_repair")
        self.add_required_key("var", "rsz_skip_hold_repair")
        self.add_required_key("var", "rsz_skip_recover_power")
