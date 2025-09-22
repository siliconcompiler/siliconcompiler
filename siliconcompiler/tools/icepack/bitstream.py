from siliconcompiler import Task


class BitstreamTask(Task):
    '''
    Generate a bitstream for the ICE40 FPGA
    '''
    def tool(self):
        return "icepack"

    def task(self):
        return "bitstream"

    def setup(self):
        super().setup()

        self.set_exe("icepack")

        self.add_input_file(ext="asc")
        self.add_output_file(ext="bit")

    def runtime_options(self):
        options = super().runtime_options()
        options.append(f"inputs/{self.design_topmodule}.asc")
        options.append(f"outputs/{self.design_topmodule}.bit")
        return options
