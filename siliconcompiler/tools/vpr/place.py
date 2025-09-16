import shutil

from siliconcompiler.tools.vpr import VPRTask
from siliconcompiler.tools.vpr._json_constraint import load_constraints_map
from siliconcompiler.tools.vpr._json_constraint import load_json_constraints
from siliconcompiler.tools.vpr._json_constraint import map_constraints
from siliconcompiler.tools.vpr._xml_constraint import generate_vpr_constraints_xml_file


class PlaceTask(VPRTask):
    '''
    Perform automated place with VPR
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "place"

    def setup(self):
        super().setup()

        self.add_input_file(ext="blif")

        self.add_output_file(ext="blif")
        self.add_output_file(ext="net")
        self.add_output_file(ext="place")

        for lib, fileset in self.project.get_filesets():
            if lib.has_file(fileset=fileset, filetype="vpr_pins"):
                self.add_required_key(lib, "fileset", fileset, "file", "vpr_pins")
            if lib.has_file(fileset=fileset, filetype="pcf"):
                self.add_required_key(lib, "fileset", fileset, "file", "pcf")
                self.add_required_key("library", self.project.get("fpga", "device"),
                                      "tool", "vpr", "constraintsmap")

    def pre_process(self):
        super().pre_process()

        for lib, fileset in self.project.get_filesets():
            files = lib.get_file(fileset=fileset, filetype="vpr_pins")
            if files:
                shutil.copy2(files[0], self.auto_constraints_file())
                return

        for lib, fileset in self.project.get_filesets():
            files = lib.get_file(fileset=fileset, filetype="pcf")
            if files:
                pcf_file = files[0]

                fpga = self.project.get("library", self.project.get("fpga", "device"),
                                        field="schema")
                map_file = fpga.find_files("tool", "vpr", "constraintsmap")

                constraints_map = load_constraints_map(map_file)
                json_constraints = load_json_constraints(pcf_file)
                all_place_constraints, missing_pins = map_constraints(self.logger,
                                                                      json_constraints,
                                                                      constraints_map)
                if missing_pins > 0:
                    raise ValueError(
                        "Pin constraints specify I/O ports not in this architecture")

                generate_vpr_constraints_xml_file(all_place_constraints,
                                                  self.auto_constraints_file())

    def runtime_options(self):
        options = super().runtime_options()

        options.append(f"inputs/{self.design_topmodule}.blif")

        options.append("--pack")
        options.append("--place")

        if self.get("var", "enable_images"):
            options.extend(["--graphics_commands", " ".join(self._get_common_graphics())])

        return options

    def post_process(self):
        super().post_process()

        shutil.copy2(f'inputs/{self.design_topmodule}.blif', 'outputs')
