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

from siliconcompiler.tools.bambu import convert

from siliconcompiler.library import StdCellLibrarySchema


class BambuStdCellLibrarySchema(StdCellLibrarySchema):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("bambu", "device", "str", "blah")
        self.define_tool_parameter("bambu", "clock_multiplier", "float",
                                   "scalar facto to convert from library units to ns")

    def set_bambu_device_name(self, name):
        self.set("tool", "bambu", "device", name)

    def set_bambu_clock_multiplier(self, factor):
        self.set("tool", "bambu", "clock_multiplier", factor)


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    convert.setup(chip)
    return chip


def parse_version(stdout):
    # Long multiline output, but second-to-last line looks like:
    # Version: PandA 0.9.6 - Revision 5e5e306b86383a7d85274d64977a3d71fdcff4fe-main
    version_line = stdout.split('\n')[-3]
    return version_line.split()[2]
