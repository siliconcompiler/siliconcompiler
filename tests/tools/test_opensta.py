# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
import pytest

import os.path

from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler import ASIC, Design, Flowgraph
from siliconcompiler.tools.opensta import timing

from siliconcompiler.targets import freepdk45_demo

from tools.inputimporter import ImporterTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(asic_gcd):
    flow = Flowgraph("testflow")
    flow.node("version", timing.TimingTask())
    asic_gcd.set_flow(flow)

    node = SchedulerNode(asic_gcd, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
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
@pytest.mark.timeout(300)
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

    ImporterTask.find_task(proj).set("var", "input_files",
                                     os.path.join(datadir, 'lec', 'foo.typical.sdf'))

    # Check that OpenSTA ran successfully
    assert proj.run()

    # Check that the setup and hold slacks are the expected values.
    assert proj.history("job0").get('metric', 'setupslack', step='opensta', index='0') == -0.890
    assert proj.history("job0").get('metric', 'holdslack', step='opensta', index='0') == 0.020


def test_opensta_parameter_top_n_paths():
    task = timing.TimingTask()
    task.set_opensta_topnpaths(5)
    assert task.get("var", "top_n_paths") == 5
    task.set_opensta_topnpaths(10, step='timing', index='1')
    assert task.get("var", "top_n_paths", step='timing', index='1') == 10
    assert task.get("var", "top_n_paths") == 5


def test_opensta_parameter_unique_path_groups_per_clock():
    task = timing.TimingTask()
    task.set_opensta_uniquepathgroupsperclock(True)
    assert task.get("var", "unique_path_groups_per_clock") is True
    task.set_opensta_uniquepathgroupsperclock(False, step='timing', index='1')
    assert task.get("var", "unique_path_groups_per_clock", step='timing', index='1') is False
    assert task.get("var", "unique_path_groups_per_clock") is True


def test_opensta_parameter_timing_mode():
    task = timing.TimingTask()
    task.set_opensta_timingmode('min')
    assert task.get("var", "timing_mode") == 'min'
    task.set_opensta_timingmode('max', step='timing', index='1')
    assert task.get("var", "timing_mode", step='timing', index='1') == 'max'
    assert task.get("var", "timing_mode") == 'min'
