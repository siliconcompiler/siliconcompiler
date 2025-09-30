# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
import pytest

import os.path

from siliconcompiler import ASIC, Design, Flowgraph
from siliconcompiler.tools.opensta import timing

from siliconcompiler.targets import freepdk45_demo

from tools.inputimporter import ImporterTask
from siliconcompiler.tools import get_task


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_opensta(datadir):
    design = Design("testdesign")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("foo")
        design.add_file(os.path.join("lec", "foo.vg"))
    with design.active_dataroot("root"), design.active_fileset("sdc"):
        design.add_file(os.path.join("lec", "foo.sdc"))
    proj = ASIC(design)
    proj.add_fileset(["rtl", "sdc"])
    freepdk45_demo(proj)

    flow = Flowgraph("timing")
    flow.node("opensta", timing.TimingTask())
    proj.set_flow(flow)

    # Check that OpenSTA ran successfully
    assert proj.run()

    # Check that the setup and hold slacks are the expected values.
    assert proj.history("job0").get('metric', 'setupslack', step='opensta', index='0') == -0.220
    assert proj.history("job0").get('metric', 'holdslack', step='opensta', index='0') == 0.050


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_opensta_sdf(datadir):
    design = Design("testdesign")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("foo")
        design.add_file(os.path.join("lec", "foo.vg"))
    with design.active_dataroot("root"), design.active_fileset("sdc"):
        design.add_file(os.path.join("lec", "foo.sdc"))
    proj = ASIC(design)
    proj.add_fileset(["rtl", "sdc"])
    freepdk45_demo(proj)

    flow = Flowgraph("timing")
    flow.node('import', ImporterTask())
    flow.node("opensta", timing.TimingTask())
    flow.edge('import', 'opensta')
    proj.set_flow(flow)

    get_task(proj, filter=ImporterTask).set("var", "input_files",
                                            os.path.join(datadir, 'lec', 'foo.typical.sdf'))

    # Check that OpenSTA ran successfully
    assert proj.run()

    # Check that the setup and hold slacks are the expected values.
    assert proj.history("job0").get('metric', 'setupslack', step='opensta', index='0') == -0.890
    assert proj.history("job0").get('metric', 'holdslack', step='opensta', index='0') == 0.020
