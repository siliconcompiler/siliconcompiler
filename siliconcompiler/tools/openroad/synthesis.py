from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter
from siliconcompiler.tools.openroad._apr import OpenROADRSZDRVParameter


class SynthesisTask(APRTask, OpenROADSTAParameter, OpenROADRSZDRVParameter):
    """
    Synthesizes RTL with OpenROAD's integrated synthesis and repairs design rule
    violations before placement.

    The RTL is the file written by a preceding elaboration node or, when there is none,
    the design's filesets with their include directories and defines. The design is
    always flattened and latches cannot be mapped.
    """
    def task(self):
        return "synthesis"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_synthesis.tcl")

        if f"{self.design_topmodule}.sv" in self.get_files_from_input_nodes():
            self.add_input_file(ext="sv")
        elif f"{self.design_topmodule}.v" in self.get_files_from_input_nodes():
            self.add_input_file(ext="v")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_idir(fileset):
                    self.add_required_key(lib, "fileset", fileset, "idir")
                for key in ("define", "undefine"):
                    if lib.get("fileset", fileset, key):
                        self.add_required_key(lib, "fileset", fileset, key)
                for filetype in ("systemverilog", "verilog"):
                    if lib.has_file(fileset=fileset, filetype=filetype):
                        self.add_required_key(lib, "fileset", fileset, "file", filetype)

        design = self.project.design
        fileset = self.project.get("option", "fileset")[0]
        for param in design.getkeys("fileset", fileset, "param"):
            self.add_required_key(design, "fileset", fileset, "param", param)

        self._set_reports([
            'scenarios',
            'check_setup',
            'setup',
            'unconstrained',
            'power',
            'drv_violations',
            'floating_nets',
            'overdriven_nets',
            "logicdepth"
        ])
        self.set_openroad_enableimages(False)
