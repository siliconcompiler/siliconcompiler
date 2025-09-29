import pytest

import os.path

from siliconcompiler.project import Project
from siliconcompiler import Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.chisel import convert


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_chisel(datadir):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("GCD")
        design.add_file("GCD.scala")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    assert proj.run()

    # check that compilation succeeded
    assert proj.find_result('v', step='convert') == \
        os.path.abspath("build/gcd/job0/convert/0/outputs/GCD.v")
