from siliconcompiler.tools.magic import MagicTask


class DRCTask(MagicTask):
    '''
    Extract spice netlists from a GDS file for simulation use
    '''
    def task(self):
        return "extpice"

    def setup(self):
        super().setup()

        self.add_output_file(ext="spice")
