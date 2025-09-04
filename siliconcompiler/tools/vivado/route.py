from siliconcompiler.tools.vivado import VivadoTask


class RouteTask(VivadoTask):
    '''Performs routing.'''
    def task(self):
        return "route"

    def setup(self):
        super().setup()

        self.add_input_file(ext="dcp")
        self.add_output_file(ext="vg")
        self.add_output_file(ext="dcp")
        self.add_output_file(ext="xdc")
