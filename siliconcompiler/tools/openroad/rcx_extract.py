from siliconcompiler.tools.openroad import OpenROADTask


class ORXExtractTask(OpenROADTask):
    '''
    Convert extracted results into RCX.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("corner", "str", "Parasitic corner to generate RCX file for")

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
