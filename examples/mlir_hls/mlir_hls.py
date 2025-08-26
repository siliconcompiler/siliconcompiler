#!/usr/bin/env python3

from siliconcompiler import ASICProject, DesignSchema
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.flows.asicflow import HLSASSICFlow


def main():
    # Create design
    design = DesignSchema("mlir")
    design.set_dataroot("mlir", __file__)
    with design.active_dataroot("mlir"), design.active_fileset("rtl"):
        design.set_topmodule("main_kernel")
        design.add_file("main_kernel.ll")

    # Create project
    project = ASICProject(design)

    # Define filesets
    project.add_fileset("rtl")

    # Load target
    project.load_target(freepdk45_demo.setup)

    # Load hls flow
    project.set_flow(HLSASSICFlow())

    # Run
    project.run()

    # Analyze
    project.summary()

    return project


if __name__ == '__main__':
    main()
