from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADPSMParameter

from siliconcompiler import TaskSkip


class PowerGridTask(APRTask, OpenROADSTAParameter, OpenROADPSMParameter):
    '''
    Perform power grid insertion and connectivity analysis
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("fixed_pin_keepout", "float",
                           "if > 0, applies a blockage in multiples of the routing pitch to each "
                           "fixed pin to ensure there is room for routing.", defvalue=0)
        self.add_parameter("psm_allow_missing_terminal_nets", "[str]",
                           "list of nets where a missing terminal is acceptable")

        self.add_parameter("pdn_enable", "bool", "enable power grid generation", defvalue=True)
        self.add_parameter("pdn_fileset", "[(str,str)]", "power grid definition filesets")

    def add_openroad_powergridfileset(self, library, fileset, clobber=False):
        if clobber:
            self.set("var", "pdn_fileset", (library, fileset))
        else:
            self.add("var", "pdn_fileset", (library, fileset))

    def task(self):
        return "power_grid"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_power_grid.tcl")

        self._set_reports([])

        self.add_required_key("var", "fixed_pin_keepout")
        if self.get("var", "psm_allow_missing_terminal_nets"):
            self.add_required_key("var", "psm_allow_missing_terminal_nets")

        self.add_required_key("var", "pdn_enable")
        if not self.get("var", "pdn_fileset"):
            self.__import_pdn_filesets()

        if self.get("var", "pdn_fileset"):
            self.add_required_key("var", "pdn_fileset")
            for lib, fileset in self.get("var", "pdn_fileset"):
                self.add_required_key("library", lib, "fileset", fileset, "file", "tcl")

    def __import_pdn_filesets(self):
        for lib in self.project.get("asic", "asiclib"):
            libobj = self.project.get("library", lib, field="schema")
            if libobj.valid("tool", "openroad", "power_grid_fileset"):
                for fileset in libobj.get("tool", "openroad", "power_grid_fileset"):
                    self.add_openroad_powergridfileset(lib, fileset)

    def pre_process(self):
        super().pre_process()

        if not self.get("var", "pdn_enable"):
            raise TaskSkip("power grid is disabled")
