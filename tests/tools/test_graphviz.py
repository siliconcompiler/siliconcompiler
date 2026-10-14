import pytest

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.graphviz import show, screenshot


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("task", [show.ShowTask, screenshot.ScreenshotTask])
def test_version(task, gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", task())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True
