from siliconcompiler.tools.vivado import VivadoTask


class SynthesisTask(VivadoTask):
    '''Performs FPGA synthesis.'''
    def __init__(self):
        super().__init__()

        self.add_parameter("synth_directive", "str", "synthesis directive", defvalue="Default")
        self.add_parameter("synth_mode", "str", "synthesis mode", defvalue="none")

    def task(self):
        return "syn_fpga"

    def setup(self):
        super().setup()

        self.add_input_file(ext="v")
        self.add_output_file(ext="vg")
        self.add_output_file(ext="dcp")
        self.add_output_file(ext="xdc")

        self.add_required_key("var", "synth_directive")
        self.add_required_key("var", "synth_mode")
