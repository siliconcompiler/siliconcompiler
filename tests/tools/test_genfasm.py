import pytest

from siliconcompiler import FPGA, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.genfasm.bitstream import BitstreamTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", BitstreamTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_runtime_args(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("bitstream", BitstreamTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "bitstream", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        # genfasm takes blif and various other files
        assert 'inputs/gcd.blif' in arguments
        assert '--net_file' in arguments
        assert '--place_file' in arguments
        assert '--route_file' in arguments
