import pytest

from siliconcompiler import FPGAProject, FlowgraphSchema
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.nextpnr.apr import APRTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design):
    proj = FPGAProject(gcd_design)
    proj.add_fileset("rtl")
    proj.set("fpga", "device", "ice40")

    flow = FlowgraphSchema("testflow")
    flow.node("version", APRTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True
