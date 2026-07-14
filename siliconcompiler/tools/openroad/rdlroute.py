from typing import Optional

from siliconcompiler.tools.openroad import OpenROADTask


class RDLRouteTask(OpenROADTask):
    '''
    Perform floorplanning, pin placements, macro placements and power grid generation
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("rdlroute", "[file]", "RDL routing scripts")

        self.add_parameter("fin_add_fill", "bool",
                           "true/false, when true enables adding fill, "
                           "if enabled by the PDK, to the design", defvalue=True)

    def add_openroad_rdlroute(self, file, dataroot=None, step=None, index=None, clobber=False):
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                self.set("var", "rdlroute", file, step=step, index=index)
            else:
                self.add("var", "rdlroute", file, step=step, index=index)

    def set_openroad_addfill(self, enable: bool,
                             step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables adding fill to the design.

        Args:
            enable (bool): True to enable fill, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "fin_add_fill", enable, step=step, index=index)

    def task(self):
        return "rdlroute"

    def setup(self):
        super().setup()

        self.set_script("sc_rdlroute.tcl")

        self.set_threads()

        if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vg")
        elif f"{self.design_topmodule}.v" in self.get_files_from_input_nodes():
            self.add_input_file(ext="v")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="verilog"):
                    self.add_required_key(lib, "fileset", fileset, "file", "verilog")

        # sc_rdlroute.tcl seeds the floorplan from a design DEF when one is present
        # in the active filesets; declare it required so it is hashed and copied.
        floorplan_def = False
        for lib, fileset in self.project.get_filesets():
            if lib.has_file(fileset=fileset, filetype="def"):
                self.add_required_key(lib, "fileset", fileset, "file", "def")
                floorplan_def = True

        # Without a DEF the die area is initialized from constraint,area,diearea, so it is
        # only required when not seeding the floorplan from a DEF.
        if not floorplan_def:
            self.add_required_key(self.project.constraint.area, "diearea")

        self.add_output_file(ext="vg")
        self.add_output_file(ext="def.gz")
        self.add_output_file(ext="odb.gz")

        if self.get("var", "rdlroute"):
            self.add_required_key("var", "rdlroute")
        self.add_required_key("var", "fin_add_fill")

        # sc_rdlroute.tcl loads the PDK tech LEF and per-library LEFs; declare them
        # required so they are hashed (cache) and copied (remote runs).
        for fileset in self.pdk.get("pdk", "aprtechfileset", "openroad"):
            if self.pdk.has_file(fileset=fileset, filetype="lef"):
                self.add_required_key(self.pdk, "fileset", fileset, "file", "lef")
        for asiclib in self.project.get("asic", "asiclib"):
            lib = self.project.get_library(asiclib)
            for fileset in lib.get("asic", "aprfileset"):
                if lib.has_file(fileset=fileset, filetype="lef"):
                    self.add_required_key(lib, "fileset", fileset, "file", "lef")

        self.set_openroad_addfill(False)
