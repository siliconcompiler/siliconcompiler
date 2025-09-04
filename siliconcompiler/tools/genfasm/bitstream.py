import shutil
from siliconcompiler.tools.vpr import VPRTask


class BitstreamTask(VPRTask):
    '''
    Generates a bitstream
    '''
    def __init__(self):
        super().__init__()

    def tool(self):
        return "genfasm"

    def task(self):
        return "bitstream"

    def setup(self):
        super().setup()

        self.set_exe("genfasm", clobber=True)

        self.add_input_file(ext="route")
        self.add_input_file(ext="blif")
        self.add_input_file(ext="net")
        self.add_input_file(ext="place")

        self.add_output_file(ext="fasm")

    def runtime_options(self):
        options = super().runtime_options()

        options.append(f"inputs/{self.design_topmodule}.blif")

        options.extend(['--net_file', f'inputs/{self.design_topmodule}.net'])
        options.extend(['--place_file', f'inputs/{self.design_topmodule}.place'])
        options.extend(['--route_file', f'inputs/{self.design_topmodule}.route'])

        return options

    def post_process(self):
        super().post_process()

        shutil.move(f'{self.design_topmodule}.fasm', 'outputs')
