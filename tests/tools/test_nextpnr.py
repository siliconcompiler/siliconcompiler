import pytest

from siliconcompiler import FPGA, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.nextpnr.apr import APRTask


@pytest.mark.eda
@pytest.mark.quick
def test_version(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")
    proj.set("fpga", "device", "ice40")

    flow = Flowgraph("testflow")
    flow.node("version", APRTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True
