import pytest

import os.path

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.surfer.show import ShowTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", ShowTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_runtime_args(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("show", ShowTask())
    proj.set_flow(flow)

    # Surfer expects a vcd file as input
    ShowTask.find_task(proj).set("var", "showfilepath", "test.vcd")
    with open("test.vcd", "w") as f:
        f.write("test\n")

    node = SchedulerNode(proj, "show", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert arguments == [os.path.abspath("test.vcd")]
