#!/usr/bin/env python3
# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import ASICProject, DesignSchema, FlowgraphSchema
from siliconcompiler.targets import interposer_demo
from siliconcompiler.tools.openroad.rdlroute import RDLRouteTask
from siliconcompiler.tools.klayout.drc import DRCTask


def main():
    '''
    Simple interposer example.
    '''

    # Create design
    design = DesignSchema("interposer")
    design.set_dataroot("interposer", __file__)
    with design.active_dataroot("interposer"), design.active_fileset("netlist"):
        design.set_topmodule("interposer")
        design.add_file("interposer.v")

    # Create project
    project = ASICProject(design)

    # Define filesets
    project.add_fileset("netlist")

    # Load target
    project.load_target(interposer_demo.setup)

    # Define die area
    project.get_areaconstraints().set_diearea_rectangle(1000, 500)

    # Create full flow
    flow = FlowgraphSchema("compositeflow")
    flow.graph(project.get("flowgraph", "interposerflow", field="schema"))
    flow.graph(project.get("flowgraph", "drcflow", field="schema"))
    flow.edge("write_gds", "drc")
    project.set_flow(flow)

    # Define bump locations script
    route: RDLRouteTask = project.get_task(filter=RDLRouteTask)
    route.set_dataroot("interposer", __file__)
    with route.active_dataroot("interposer"):
        route.add_openroad_rdlroute("bumps.tcl")

    # Define drc deck
    project.get_task(filter=DRCTask).set("var", "drc_name", "drc")

    # Run
    project.run()

    # Analyze
    project.summary()

    return project


if __name__ == '__main__':
    main()
