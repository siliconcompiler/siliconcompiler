import pytest

from siliconcompiler import FPGA, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.vivado import syn_fpga, place, route, bitstream


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_synthesis_version(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", syn_fpga.SynthesisTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_place_version(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", place.PlaceTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_route_version(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", route.RouteTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_bitstream_version(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", bitstream.BitstreamTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_vivado_parameter_synth_directive():
    task = syn_fpga.SynthesisTask()
    task.set_vivado_synthdirective('Remap')
    assert task.get("var", "synth_directive") == 'Remap'
    task.set_vivado_synthdirective('AlternateRoutability', step='syn_fpga', index='1')
    assert task.get("var", "synth_directive", step='syn_fpga', index='1') == 'AlternateRoutability'
    assert task.get("var", "synth_directive") == 'Remap'


def test_vivado_parameter_synth_mode():
    task = syn_fpga.SynthesisTask()
    task.set_vivado_synthmode('out_of_context')
    assert task.get("var", "synth_mode") == 'out_of_context'
    task.set_vivado_synthmode('flow', step='syn_fpga', index='1')
    assert task.get("var", "synth_mode", step='syn_fpga', index='1') == 'flow'
    assert task.get("var", "synth_mode") == 'out_of_context'
