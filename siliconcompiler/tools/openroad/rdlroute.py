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

        self.add_output_file(ext="vg")
        self.add_output_file(ext="def")
        self.add_output_file(ext="odb")

        if self.get("var", "rdlroute"):
            self.add_required_key("var", "rdlroute")
        self.add_required_key("var", "fin_add_fill")

        self.set("var", "fin_add_fill", False)
