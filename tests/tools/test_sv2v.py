import pytest

from siliconcompiler.project import Project
from siliconcompiler import Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.sv2v.convert import ConvertTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_runtime_opts(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 2
        assert arguments == ['inputs/gcd.sv', '--write=outputs/gcd.v']
