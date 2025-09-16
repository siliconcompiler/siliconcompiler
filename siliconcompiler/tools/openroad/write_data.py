from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADPSMParameter


class WriteViewsTask(APRTask, OpenROADSTAParameter, OpenROADPSMParameter):
    '''
    Write output files
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("ord_abstract_lef_bloat_layers", "bool",
                           "true/false, fill all layers when writing the abstract lef",
                           defvalue=True)
        self.add_parameter("ord_abstract_lef_bloat_factor", "int",
                           "Factor to apply when writing the abstract lef", defvalue=10)

        self.add_parameter("write_cdl", "bool",
                           "true/false, when true enables writing the CDL file for the design",
                           defvalue=False)
        self.add_parameter("write_spef", "bool",
                           "true/false, when true enables writing the SPEF file for the design",
                           defvalue=True)
        self.add_parameter("use_spef", "bool",
                           "true/false, when true enables reading in SPEF files.")
        self.add_parameter("write_liberty", "bool",
                           "true/false, when true enables writing the liberty timing model for "
                           "the design", defvalue=True)
        self.add_parameter("write_sdf", "bool",
                           "true/false, when true enables writing the SDF timing model for the "
                           "design", defvalue=True)

        self.add_parameter("pex_corners", "{str}", "set of pex corners to perform extraction on")

    def task(self):
        return "write_data"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_write_data.tcl")

        self.set("var", "pex_corners", list(self._get_pex_mapping().values()))

        self.set("var", "use_spef", self.get("var", "write_spef"))

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
            'ir_drop',
            'clock_placement',
            'clock_trees',
            'optimization_placement'
        ])

        # Setup outputs
        self.add_output_file(ext="lef")

        if self.get("var", "write_cdl"):
            self.add_output_file(ext="cdl")
        if self.get("var", "write_spef"):
            self.add_required_key("var", "pex_corners")
            self.add_required_key("var", "use_spef")
            for corner in self.get("var", "pex_corners"):
                self.add_output_file(ext=f"{corner}.spef")
        if self.get("var", "write_liberty"):
            for corner in self.project.getkeys("constraint", "timing"):
                self.add_output_file(ext=f"{corner}.lib")
        if self.get("var", "write_sdf"):
            for corner in self.project.getkeys("constraint", "timing"):
                self.add_output_file(ext=f"{corner}.sdf")

        self.add_required_key("var", "ord_abstract_lef_bloat_layers")
        self.add_required_key("var", "ord_abstract_lef_bloat_factor")
        self.add_required_key("var", "write_cdl")
        self.add_required_key("var", "write_spef")
        self.add_required_key("var", "write_liberty")
        self.add_required_key("var", "write_sdf")
