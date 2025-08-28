from siliconcompiler.tools.magic import MagicTask


class ExtractTask(MagicTask):
    '''
    Extract spice netlists from a GDS file for simulation use
    '''
    def task(self):
        return "extspice"

    def setup(self):
        super().setup()

        self.add_output_file(ext="spice")
