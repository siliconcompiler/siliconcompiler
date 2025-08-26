#!/usr/bin/env python3

from siliconcompiler import FPGAProject, DesignSchema, FPGASchema
from siliconcompiler.flows import fpgaflow


def main():
    '''RTL2bitstream flow'''

    # Create design
    design = DesignSchema("blinky")
    design.set_dataroot("blinky", __file__)
    with design.active_dataroot("blinky"), design.active_fileset("rtl"):
        design.set_topmodule("blinky")
        design.add_file("blinky.v")
    with design.active_dataroot("blinky"), design.active_fileset("pcf"):
        design.add_file("icebreaker.pcf")

    # Create project
    project = FPGAProject(design)

    # Define filesets
    project.add_fileset("rtl")
    project.add_fileset("pcf")

    # Load FPGA
    fpga = FPGASchema("ice40")
    fpga.set_partname("ice40up5k-sg48")
    project.set_fpga(fpga)

    # Load flow
    project.set_flow(fpgaflow.FPGANextPNRFlow())

    # Run
    assert project.run()

    # Analyze
    project.summary()

    return project


if __name__ == '__main__':
    main()
