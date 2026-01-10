from typing import Optional
from siliconcompiler.tools.vivado import VivadoTask


class SynthesisTask(VivadoTask):
    '''Performs FPGA synthesis.'''
    def __init__(self):
        super().__init__()

        self.add_parameter("synth_directive", "str", "synthesis directive", defvalue="Default")
        self.add_parameter("synth_mode", "str", "synthesis mode", defvalue="none")

    def set_vivado_synthdirective(self, directive: str,
                                  step: Optional[str] = None,
                                  index: Optional[str] = None):
        """
        Sets the synthesis directive.

        Args:
            directive (str): The synthesis directive.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "synth_directive", directive, step=step, index=index)

    def set_vivado_synthmode(self, mode: str,
                             step: Optional[str] = None,
                             index: Optional[str] = None):
        """
        Sets the synthesis mode.

        Args:
            mode (str): The synthesis mode.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "synth_mode", mode, step=step, index=index)

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
