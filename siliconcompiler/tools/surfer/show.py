import os.path

from siliconcompiler import ShowTask


class ShowTask(ShowTask):
    def tool(self):
        return "surfer"

    def parse_version(self, stdout):
        # surfer 0.3.0
        return stdout.strip().split()[1]

    def get_supported_show_extentions(self):
        return ["vcd"]

    def setup(self):
        super().setup()

        self.set_exe("surfer", vswitch="--version")
        self.add_version(">=0.3.0")

        if f"{self.design_topmodule}.vcd" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vcd")
        else:
            self.add_required_key("var", "showfilepath")

    def runtime_options(self):
        options = super().runtime_options()

        # Get VCD file
        if os.path.exists(f'inputs/{self.design_topmodule}.vcd'):
            dump = f'inputs/{self.design_topmodule}.vcd'
        else:
            dump = self.find_files('var', 'showfilepath')
        options.append(dump)

        return options
