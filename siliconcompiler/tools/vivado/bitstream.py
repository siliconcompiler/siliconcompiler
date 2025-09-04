from siliconcompiler.tools.vivado import VivadoTask


class BitstreamTask(VivadoTask):
    '''Generates bitstream of implemented design.'''
    def task(self):
        return "bitstream"

    def setup(self):
        super().setup()

        self.add_input_file(ext="dcp")
        self.add_output_file(ext="vg")
        self.add_output_file(ext="dcp")
        self.add_output_file(ext="xdc")
        self.add_output_file(ext="bit")
