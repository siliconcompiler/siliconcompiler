'''
The primary objective of the PandA project is to develop a usable framework that will
enable the research of new ideas in the HW-SW Co-Design field.

The PandA framework includes methodologies supporting the research on high-level synthesis
of hardware accelerators, on parallelism extraction for embedded systems, on hardware/software
partitioning and mapping, on metrics for performance estimation of embedded software
applications and on dynamic reconfigurable devices.

Documentation: https://github.com/ferrandi/PandA-bambu

Sources: https://github.com/ferrandi/PandA-bambu

Installation: https://panda.dei.polimi.it/?page_id=88
'''
from siliconcompiler import StdCellLibrary


class BambuStdCellLibrary(StdCellLibrary):
    """
    Schema for a standard cell library specifically for the Bambu tool.

    This class extends the base StdCellLibrary to define and manage
    tool-specific parameters required by Bambu, such as the device name
    and a clock multiplier factor.
    """

    def __init__(self):
        super().__init__()

        self.define_tool_parameter("bambu", "device", "str",
                                   "name of the target device for bambu.")
        self.define_tool_parameter("bambu", "clock_multiplier", "float",
                                   "scalar facto to convert from library units to ns.")

    def set_bambu_device_name(self, name):
        """
        Sets the name of the device to be used with the Bambu tool.

        Args:
            name (str): The name of the device.
        """
        self.set("tool", "bambu", "device", name)

    def set_bambu_clock_multiplier(self, factor):
        """
        Sets the clock multiplier factor for the Bambu tool.

        This factor is used to convert timing values from the standard
        cell library's units to nanoseconds.

        Args:
            factor (float): The scalar factor for the clock conversion.
        """
        self.set("tool", "bambu", "clock_multiplier", factor)
