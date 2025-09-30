import pytest

import os.path

from siliconcompiler.targets import freepdk45_demo

from tools.inputimporter import ImporterTask

from siliconcompiler import ASIC, Design, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.yosys.lec_asic import ASICLECTask
from siliconcompiler.tools import get_task


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design):
    proj = ASIC(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", ASICLECTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_yosys_lec(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("lec")
    flow.node('import', ImporterTask())
    flow.node("lec", ASICLECTask())
    flow.edge('import', 'lec')
    proj.set_flow(flow)

    get_task(proj, filter=ImporterTask).add("var", "input_files",
                                            os.path.join(datadir, 'lec', 'foo.v'))
    get_task(proj, filter=ImporterTask).add("var", "input_files",
                                            os.path.join(datadir, 'lec', 'foo.vg'))

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='lec', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_yosys_lec_broken(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("lec")
    flow.node('import', ImporterTask())
    flow.node("lec", ASICLECTask())
    flow.edge('import', 'lec')
    proj.set_flow(flow)

    get_task(proj, filter=ImporterTask).add(
        "var", "input_files", os.path.join(datadir, 'lec', 'broken', 'foo.v'))
    get_task(proj, filter=ImporterTask).add(
        "var", "input_files", os.path.join(datadir, 'lec', 'broken', 'foo.vg'))

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='lec', index='0') == 2
