from typing import Optional, Union

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

    def set_openroad_benchmaxlayer(self, layer: str,
                                   step: Optional[str] = None,
                                   index: Optional[Union[int, str]] = None):
        """
        Sets the maximum layer to generate the extraction bench for.

        Args:
            layer (str): The layer name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "max_layer", layer, step=step, index=index)

    def set_openroad_benchlength(self, length: float,
                                 step: Optional[str] = None,
                                 index: Optional[Union[int, str]] = None):
        """
        Sets the length of bench wires.

        Args:
            length (float): The length in microns.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "bench_length", length, step=step, index=index)

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
