import pytest

import os.path

from siliconcompiler import ASIC, Design, Flowgraph
from siliconcompiler.flows.drcflow import DRCFlow
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.targets import skywater130_demo
from siliconcompiler.tools.magic import drc, extspice


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(asic_gcd):
    flow = Flowgraph("testflow")
    flow.node("version", drc.DRCTask())
    asic_gcd.set_flow(flow)

    node = SchedulerNode(asic_gcd, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_extspice_version(asic_gcd):
    flow = Flowgraph("testflow")
    flow.node("version", extspice.ExtractTask())
    asic_gcd.set_flow(flow)

    node = SchedulerNode(asic_gcd, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_drc_reports_error_outside_cell_bbox(datadir):
    # sky130 layout with a 5um x 5um met1 square and, as its rightmost shape, a
    # 0.10um wide met1 strip (met1.1 requires 0.14um). Magic marks the width
    # error to the right of the strip, outside the cell's bounding box.
    design = Design("edge_violation")
    with design.active_fileset("layout"):
        design.set_topmodule("edge_violation")
        design.add_file(os.path.join(datadir, "magic_edge_violation.gds"))

    proj = ASIC(design)
    proj.add_fileset("layout")
    skywater130_demo(proj)
    proj.set_flow(DRCFlow(tool="magic"))

    assert proj.run()
    assert proj.history("job0").get('metric', 'drcs', step='drc', index='0') == 1
