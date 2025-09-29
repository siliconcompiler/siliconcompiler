import pytest

from siliconcompiler.project import Project
from siliconcompiler import Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.gtkwave import show


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design, display):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", show.ShowTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True
