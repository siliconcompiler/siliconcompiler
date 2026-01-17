import pytest

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.graphviz import show, screenshot


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_show_version(gcd_design, display):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", show.ShowTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        # Graphviz doesn't require an exe check like other tools
        assert True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_screenshot_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", screenshot.ScreenshotTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        # Graphviz doesn't require an exe check like other tools
        assert True
