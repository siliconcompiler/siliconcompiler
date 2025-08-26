from siliconcompiler.tools.vivado import VivadoTask


class PlaceTask(VivadoTask):
    '''Performs placement.'''
    def task(self):
        return "place"

    def setup(self):
        super().setup()

        self.add_input_file(ext="dcp")
        self.add_output_file(ext="vg")
        self.add_output_file(ext="dcp")
        self.add_output_file(ext="xdc")
