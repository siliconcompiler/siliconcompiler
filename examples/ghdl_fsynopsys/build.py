#!/usr/bin/env python3

from siliconcompiler import ASICProject, DesignSchema
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.flows.asicflow import VHDLASICFlow
from siliconcompiler.tools.ghdl.convert import ConvertTask


def main():
    # Create design
    design = DesignSchema("ghdl_fsynopsys")
    design.set_dataroot("ghdl_fsynopsys", __file__)
    with design.active_dataroot("ghdl_fsynopsys"), design.active_fileset("rtl"):
        design.set_topmodule("binary_4_bit_adder_top")
        design.add_file("binary_4_bit_adder_top.vhd")

    # Create project
    project = ASICProject(design)

    # Define filesets
    project.add_fileset("rtl")

    # Load target
    project.load_target(freepdk45_demo.setup)

    # Load hls flow
    project.set_flow(VHDLASICFlow())

    # Adjust options
    project.get_task(filter=ConvertTask).set_usefsynopsys(True)

    # Run
    project.run()

    # Analyze
    project.summary()

    return project


if __name__ == '__main__':
    main()
