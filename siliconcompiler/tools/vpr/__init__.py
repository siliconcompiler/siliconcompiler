from typing import List, Union

from siliconcompiler import FPGASchema


class VPRFPGA(FPGASchema):
    """
    Schema for defining library parameters specifically for the
    VPR (Verilog Place and Route) tool.

    This class extends the base FPGASchema to manage various settings
    related to VPR, such as device information, channel width, resource types,
    and input file paths for the architecture and routing graph.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("vpr", "devicecode", "str",
                                   "The name or code for the target FPGA device.")
        self.define_tool_parameter("vpr", "channelwidth", "int",
                                   "The channel width to be used during routing.")

        self.define_tool_parameter("vpr", "registers", "{str}",
                                   "A set of supported register types.")
        self.define_tool_parameter("vpr", "brams", "{str}",
                                   "A set of supported block RAM types.")
        self.define_tool_parameter("vpr", "dsps", "{str}",
                                   "A set of supported DSP types.")

        self.define_tool_parameter("vpr", "archfile", "file",
                                   "The path to the VPR architecture description file.")
        self.define_tool_parameter("vpr", "graphfile", "file",
                                   "The path to the VPR routing graph file.")
        self.define_tool_parameter("vpr", "constraintsmap", "file",
                                   "The path to the VPR constraints map file.")

        self.define_tool_parameter("vpr", "clock_model", "<ideal,route,dedicated_network>",
                                   "The clock modeling strategy to be used.")

    def set_vpr_devicecode(self, name: str):
        """
        Sets the device code for VPR.

        Args:
            name (str): The name or code of the device.
        """
        return self.set("tool", "vpr", "devicecode", name)

    def set_vpr_channelwidth(self, width: int):
        """
        Sets the channel width for VPR routing.

        Args:
            width (int): The channel width value.
        """
        return self.set("tool", "vpr", "channelwidth", width)

    def add_vpr_registertype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds one or more register types to the list of supported registers.

        Args:
            name (Union[str, List[str]], optional): The register type or a list of types.
                                                    Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list.
                                      If False, adds to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "vpr", "registers", name)
        else:
            return self.add("tool", "vpr", "registers", name)

    def add_vpr_bramtype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds one or more block RAM types to the list of supported BRAMs.

        Args:
            name (Union[str, List[str]], optional): The BRAM type or a list of types.
                                                    Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list.
                                      If False, adds to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "vpr", "brams", name)
        else:
            return self.add("tool", "vpr", "brams", name)

    def add_vpr_dsptype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds one or more DSP types to the list of supported DSPs.

        Args:
            name (Union[str, List[str]], optional): The DSP type or a list of types.
                                                    Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list.
                                      If False, adds to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "vpr", "dsps", name)
        else:
            return self.add("tool", "vpr", "dsps", name)

    def set_vpr_archfile(self, file: str, dataroot: str = None):
        """
        Sets the path to the VPR architecture file.

        Args:
            file (str): The path to the architecture file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.set("tool", "vpr", "archfile", file)

    def set_vpr_graphfile(self, file: str, dataroot: str = None):
        """
        Sets the path to the VPR routing graph file.

        Args:
            file (str): The path to the routing graph file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.set("tool", "vpr", "graphfile", file)

    def set_vpr_constraintsmap(self, file: str, dataroot: str = None):
        """
        Sets the path to the VPR constraints map file.

        Args:
            file (str): The path to the constraints map file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.set("tool", "vpr", "constraintsmap", file)

    def set_vpr_clockmodel(self, model: str):
        """
        Sets the clock modeling strategy.

        Args:
            model (str): The name of the clock model to use
                         (e.g., 'ideal', 'route', or 'dedicated_network').
        """
        return self.set("tool", "vpr", "clock_model", model)
