from typing import Optional, Union

from siliconcompiler.tools.openroad import OpenROADTask


class ORXExtractTask(OpenROADTask):
    '''
    Convert extracted results into RCX.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("corner", "str", "Parasitic corner to generate RCX file for")

    def set_openroad_rcxcorner(self, corner: str,
                               step: Optional[str] = None, index: Optional[Union[int, str]] = None):
        """
        Sets the parasitic corner to generate the RCX file for.

        Args:
            corner (str): The parasitic corner name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "corner", corner, step=step, index=index)

    def task(self):
        return "rcx_extract"

    def setup(self):
        self.set_threads(1)

        super().setup()

        self.set_script("sc_rcx.tcl")

        self.add_required_key("var", "corner")

        corner = self.get("var", "corner")

        self.add_input_file(ext="def")
        self.add_input_file(ext=f"{corner}.spef")
        self.add_output_file(ext=f"{corner}.rcx")
