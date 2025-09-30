# Copyright 2025 Zero ASIC Corporation

from siliconcompiler import FPGA, Design
from siliconcompiler.flows.fpgaflow import FPGAVPROpenSTAFlow

from siliconcompiler.tools.vpr import VPRFPGA
from siliconcompiler.tools.yosys import YosysFPGA
from siliconcompiler.tools.opensta import OpenSTAFPGA


class Z1000(YosysFPGA, VPRFPGA, OpenSTAFPGA):
    '''
    z1000 is the first in a series of open FPGA architectures.
    The baseline z1000 part is an architecture with 2K LUTs
    and no hard macros.
    '''
    def __init__(self):
        super().__init__()
        self.set_name("z1000")

        self.set_dataroot("siliconcompiler", "python://siliconcompiler")
        self.package.set_vendor("ZeroASIC")
        self.set_lutsize(4)

        self.add_yosys_registertype(["dff", "dffr", "dffe", "dffer"])
        self.add_yosys_featureset(["async_reset", "enable"])
        with self.active_dataroot("siliconcompiler"):
            self.set_yosys_flipfloptechmap("data/demo_fpga/tech_flops.v")

        self.set_vpr_devicecode("z1000")
        self.set_vpr_clockmodel("route")
        self.set_vpr_channelwidth(100)
        self.add_vpr_registertype(["dff", "dffr", "dffe", "dffer"])
        with self.active_dataroot("siliconcompiler"):
            self.set_vpr_archfile("data/demo_fpga/z1000.xml")
            self.set_vpr_graphfile("data/demo_fpga/z1000_rr_graph.xml")
            self.set_vpr_constraintsmap("data/demo_fpga/z1000_constraint_map.json")

        self.set_vpr_router_lookahead("classic")

        with self.active_dataroot("siliconcompiler"):
            with self.active_fileset("z1000_opensta_liberty_files"):
                self.add_file("data/demo_fpga/vtr_primitives.lib")
                self.add_file("data/demo_fpga/tech_flops.lib")
                self.add_opensta_liberty_fileset()


class FPGADemo(FPGA):
    '''
    "Self-test" target which builds a small 8-bit counter design as an FPGA,
    targeting the z1000.

    This target is intended for testing purposes only,
    to verify that SiliconCompiler is installed and configured correctly.
    '''

    def __init__(self):
        super().__init__()

        design = Design("heartbeat")
        design.set_dataroot("heartbeat", "python://siliconcompiler")
        with design.active_dataroot("heartbeat"), design.active_fileset("rtl"):
            design.set_topmodule("heartbeat")
            design.add_file("data/heartbeat.v")
            design.set_param("N", "8")
        with design.active_dataroot("heartbeat"), design.active_fileset("sdc"):
            design.add_file("data/demo_fpga/heartbeat.sdc")
        with design.active_dataroot("heartbeat"), design.active_fileset("pcf"):
            design.add_file("data/demo_fpga/heartbeat.pcf")

        # Set design
        self.set_design(design)
        self.add_fileset("rtl")
        self.add_fileset("sdc")
        self.add_fileset("pcf")

        # Set FPGA
        self.set_fpga(Z1000())

        # Set flow
        self.set_flow(FPGAVPROpenSTAFlow())


if __name__ == "__main__":
    proj = FPGADemo.create_cmdline(
        "fpga_demo",
        description="\"Self-test\" target which builds a small 8-bit counter design as an FPGA, "
                    "targeting the z1000.",
        switchlist=["-remote"])
    proj.run()
    proj.summary()
