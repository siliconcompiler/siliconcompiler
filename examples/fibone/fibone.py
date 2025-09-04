#!/usr/bin/env python3

from siliconcompiler import ASICProject, DesignSchema
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.flows.asicflow import ASICFlow
from siliconcompiler.tools.bluespec import convert


def main():
    # Create design
    design = DesignSchema("fibone")
    design.set_dataroot("fibone", __file__)
    with design.active_dataroot("fibone"), design.active_fileset("rtl"):
        design.set_topmodule("mkFibOne")
        design.add_file("FibOne.bsv")

    # Create project
    project = ASICProject(design)

    # Define filesets
    project.add_fileset("rtl")

    # Load target
    project.load_target(freepdk45_demo.setup)

    # Load bluespec flow
    flow = ASICFlow("asic-bluespec")
    flow.remove_node("elaborate")
    flow.node("convert", convert.ConvertTask())
    flow.edge("convert", "synthesis")
    project.set_flow(flow)

    # Run
    project.run()

    # Analyze
    project.summary()

    return project


if __name__ == '__main__':
    main()
