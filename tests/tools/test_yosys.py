import pytest

import os.path

from siliconcompiler.targets import freepdk45_demo

from tools.inputimporter import ImporterTask

from siliconcompiler import ASICProject, DesignSchema, FlowgraphSchema
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.yosys.lec_asic import ASICLECTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design):
    proj = ASICProject(gcd_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
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
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASICProject(design)
    proj.add_fileset(["rtl"])
    proj.load_target(freepdk45_demo.setup)

    flow = FlowgraphSchema("lec")
    flow.node('import', ImporterTask())
    flow.node("lec", ASICLECTask())
    flow.edge('import', 'lec')
    proj.set_flow(flow)

    proj.get_task(filter=ImporterTask).add("var", "input_files",
                                           os.path.join(datadir, 'lec', 'foo.v'))
    proj.get_task(filter=ImporterTask).add("var", "input_files",
                                           os.path.join(datadir, 'lec', 'foo.vg'))

    assert proj.run()
    assert proj.get('metric', 'drvs', step='lec', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_yosys_lec_broken(datadir):
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASICProject(design)
    proj.add_fileset(["rtl"])
    proj.load_target(freepdk45_demo.setup)

    flow = FlowgraphSchema("lec")
    flow.node('import', ImporterTask())
    flow.node("lec", ASICLECTask())
    flow.edge('import', 'lec')
    proj.set_flow(flow)

    proj.get_task(filter=ImporterTask).add(
        "var", "input_files", os.path.join(datadir, 'lec', 'broken', 'foo.v'))
    proj.get_task(filter=ImporterTask).add(
        "var", "input_files", os.path.join(datadir, 'lec', 'broken', 'foo.vg'))

    assert proj.run()
    assert proj.get('metric', 'drvs', step='lec', index='0') == 2
