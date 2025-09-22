from siliconcompiler import Task


class ConvertTask(Task):
    '''
    Convert SystemVerilog to verilog
    '''
    def __init__(self):
        super().__init__()

    def tool(self):
        return "sv2v"

    def task(self):
        return "convert"

    def parse_version(self, stdout):
        # 0.0.7-130-g1aa30ea
        stdout = stdout.strip()
        if '-' in stdout:
            return '-'.join(stdout.split('-')[:-1])
        return stdout

    def setup(self):
        super().setup()

        self.set_exe("sv2v", vswitch="--numeric-version")
        self.add_version(">=0.0.9")

        self.set_threads(1)
        self.add_input_file(ext="sv")
        self.add_output_file(ext="v")

    def runtime_options(self):
        options = super().runtime_options()
        options.append(f"inputs/{self.design_topmodule}.sv")
        options.append(f"--write=outputs/{self.design_topmodule}.v")
        return options
