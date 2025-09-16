from siliconcompiler.tools.openroad import OpenROADTask


class ORXBenchTask(OpenROADTask):
    '''
    Builds the RCX extraction bench
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("max_layer", "str", "Maximum layer to generate extraction bench for")
        self.add_parameter("bench_length", "float", "Length of bench wires",
                           defvalue=100, units="um")

    def task(self):
        return "rcx_bench"

    def setup(self):
        self.set_threads(1)

        super().setup()

        self.set_script("sc_rcx.tcl")

        self.add_required_key("var", "max_layer")
        self.add_required_key("var", "bench_length")

        self.add_output_file(ext="def")
        self.add_output_file(ext="vg")
