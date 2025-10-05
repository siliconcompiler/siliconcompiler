import pytest

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.montage import tile
from siliconcompiler.tools import get_task


@pytest.mark.eda
@pytest.mark.quick
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", tile.TileTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_runtime_opts(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("tile", tile.TileTask())
    proj.set_flow(flow)

    assert get_task(proj, filter=tile.TileTask).set("var", "bins", (4, 3))

    node = SchedulerNode(proj, "tile", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 17
        assert arguments == [
            'inputs/gcd_X0_Y0.png', 'inputs/gcd_X1_Y0.png',
            'inputs/gcd_X2_Y0.png', 'inputs/gcd_X3_Y0.png',
            'inputs/gcd_X0_Y1.png', 'inputs/gcd_X1_Y1.png',
            'inputs/gcd_X2_Y1.png', 'inputs/gcd_X3_Y1.png',
            'inputs/gcd_X0_Y2.png', 'inputs/gcd_X1_Y2.png',
            'inputs/gcd_X2_Y2.png', 'inputs/gcd_X3_Y2.png',
            '-tile', '4x3', '-geometry', '+0+0', 'outputs/gcd.png']
