import pytest

from siliconcompiler import SimProject
from siliconcompiler import Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.xdm import convert
from siliconcompiler.tools.xyce import simulate


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_xdm_version(gcd_design):
    proj = SimProject(gcd_design)
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
def test_xyce_version(gcd_design):
    proj = SimProject(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", simulate.SimulateTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True
