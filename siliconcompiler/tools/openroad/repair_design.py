from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADRSZDRVParameter


class RepairDesignTask(APRTask, OpenROADSTAParameter, OpenROADRSZDRVParameter):
    '''
    Perform timing repair and tie-off cell insertion
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("ifp_tie_separation", "float",
                           "maximum distance between tie high/low cells in microns",
                           defvalue=0, unit="um")

        self.add_parameter("rsz_buffer_inputs", "bool",
                           "true/false, when true enables adding buffers to the input ports",
                           defvalue=False)
        self.add_parameter("rsz_buffer_outputs", "bool",
                           "true/false, when true enables adding buffers to the output ports",
                           defvalue=False)

    def task(self):
        return "repair_design"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_repair_design.tcl")

        self._set_reports([
            'setup',
            'unconstrained',
            'power',
            'drv_violations',
            'fmax',
            'report_buffers',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'optimization_placement',
            'module_view'
        ])

        self.add_required_key("var", "ifp_tie_separation")
        self.add_required_key("var", "rsz_buffer_inputs")
        self.add_required_key("var", "rsz_buffer_outputs")
