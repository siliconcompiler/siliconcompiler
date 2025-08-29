# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
import pytest

import os.path

from siliconcompiler import ASICProject, DesignSchema, FlowgraphSchema
from siliconcompiler.tools.opensta import timing

from siliconcompiler.targets import freepdk45_demo

from tools.inputimporter import ImporterTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_opensta(datadir):
    design = DesignSchema("testdesign")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("foo")
        design.add_file(os.path.join("lec", "foo.vg"))
    with design.active_dataroot("root"), design.active_fileset("sdc"):
        design.add_file(os.path.join("lec", "foo.sdc"))
    proj = ASICProject(design)
    proj.add_fileset(["rtl", "sdc"])
    proj.load_target(freepdk45_demo.setup)

    flow = FlowgraphSchema("timing")
    flow.node("opensta", timing.TimingTask())
    proj.set_flow(flow)

    # Check that OpenSTA ran successfully
    assert proj.run()

    # Check that the setup and hold slacks are the expected values.
    assert proj.get('metric', 'setupslack', step='opensta', index='0') == -0.220
    assert proj.get('metric', 'holdslack', step='opensta', index='0') == 0.050


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_opensta_sdf(datadir):
    design = DesignSchema("testdesign")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("foo")
        design.add_file(os.path.join("lec", "foo.vg"))
    with design.active_dataroot("root"), design.active_fileset("sdc"):
        design.add_file(os.path.join("lec", "foo.sdc"))
    proj = ASICProject(design)
    proj.add_fileset(["rtl", "sdc"])
    proj.load_target(freepdk45_demo.setup)

    flow = FlowgraphSchema("timing")
    flow.node('import', ImporterTask())
    flow.node("opensta", timing.TimingTask())
    flow.edge('import', 'opensta')
    proj.set_flow(flow)

    proj.get_task(filter=ImporterTask).set("var", "input_files",
                                           os.path.join(datadir, 'lec', 'foo.typical.sdf'))

    # Check that OpenSTA ran successfully
    assert proj.run()

    # Check that the setup and hold slacks are the expected values.
    assert proj.get('metric', 'setupslack', step='opensta', index='0') == -0.890
    assert proj.get('metric', 'holdslack', step='opensta', index='0') == 0.020
