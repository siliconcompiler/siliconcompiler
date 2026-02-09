import pytest

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.xdm import convert
from siliconcompiler.tools.xyce import simulate


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_xdm_version(gcd_design):
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
@pytest.mark.timeout(300)
def test_xyce_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", simulate.SimulateTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_xdm_parameter_rename():
    task = convert.ConvertTask()
    task.set_xdm_rename(False)
    assert task.get("var", "rename") is False
    task.set_xdm_rename(True, step='convert', index='1')
    assert task.get("var", "rename", step='convert', index='1') is True
    assert task.get("var", "rename") is False
