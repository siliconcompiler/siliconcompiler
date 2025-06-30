#!/usr/bin/env python3

from siliconcompiler import ASICProject, DesignSchema
from siliconcompiler.targets import freepdk45_demo


def rtl2gds():
    '''RTL2GDS flow'''

    # Create design
    design = DesignSchema("aes")
    design.set_dataroot("aes", __file__)
    with design.active_dataroot("aes"), design.active_fileset("rtl"):
        design.set_topmodule("aes")
        design.add_file("aes.v")
    with design.active_dataroot("aes"), design.active_fileset("sdc"):
        design.add_file("aes.sdc")

    # Create project
    project = ASICProject(design)

    # Define filesets
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    # Load target
    project.load_target(freepdk45_demo.setup)

    # RUN
    project.run()

    # ANALYZE
    project.summary()

    return project


if __name__ == '__main__':
    rtl2gds()
