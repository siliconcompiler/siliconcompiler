import pytest

import re

from siliconcompiler import Flowgraph

from siliconcompiler.flows.asicflow import (
    ASICFlow,
    SV2VASICFlow,
    HLSASICFlow,
    VHDLASICFlow,
    ChiselASICFlow,
    FloorplanningFlow,
    PlacementFlow,
    ClockTreeSynthesisFlow,
    RoutingFlow,
    FillerCellFlow,
    MetalFillFlow
)
from siliconcompiler.flows.checklibraryflow import CheckLibraryFlow
from siliconcompiler.flows.drcflow import DRCFlow, KlayoutDRCFlow, MagicDRCFlow
from siliconcompiler.flows.dvflow import (
    DVFlow,
    IcarusDVFlow,
    IcarusCocotbDVFlow,
    VerilatorDVFlow,
    VerilatorCocotbDVFlow,
    XyceDVFlow,
    XDMXyceDVFlow
)
from siliconcompiler.flows.elaborationflow import (
    ElaborationFlow,
    SlangElaborationFlow,
    SV2VElaborationFlow,
    HLSElaborationFlow,
    VHDLElaborationFlow,
    ChiselElaborationFlow,
    BluespecElaborationFlow
)
from siliconcompiler.flows.formalflow import PropertyCheckFlow
from siliconcompiler.flows.fpgaflow import (
    FPGAXilinxFlow,
    FPGANextPNRFlow,
    FPGAVPRFlow,
    FPGAVPROpenSTAFlow
)
from siliconcompiler.flows.openroad_pex import (
    GenerateOpenRCXFlow,
    GeneratePEXEstimateFlow,
    PEXCalibrateFlow
)
from siliconcompiler.flows.highresscreenshotflow import HighResScreenshotFlow
from siliconcompiler.flows.img2streamflow import Img2StreamFlow
from siliconcompiler.flows.interposerflow import InterposerFlow
from siliconcompiler.flows.lintflow import LintFlow, VerilatorLintFlow, SlangLintFlow
from siliconcompiler.flows.lvsflow import MagicLVSFlow
from siliconcompiler.flows.showflow import ShowFlow
from siliconcompiler.flows.signoffflow import SignoffFlow
from siliconcompiler.flows.synflow import SynthesisFlow


@pytest.mark.parametrize("flow", [
    CheckLibraryFlow,
    ASICFlow,
    SV2VASICFlow,
    HLSASICFlow,
    VHDLASICFlow,
    ChiselASICFlow,
    FloorplanningFlow,
    PlacementFlow,
    ClockTreeSynthesisFlow,
    RoutingFlow,
    FillerCellFlow,
    MetalFillFlow,
    DRCFlow,
    KlayoutDRCFlow,
    MagicDRCFlow,
    DVFlow,
    IcarusDVFlow,
    IcarusCocotbDVFlow,
    VerilatorDVFlow,
    VerilatorCocotbDVFlow,
    XyceDVFlow,
    XDMXyceDVFlow,
    ElaborationFlow,
    SlangElaborationFlow,
    SV2VElaborationFlow,
    HLSElaborationFlow,
    VHDLElaborationFlow,
    ChiselElaborationFlow,
    BluespecElaborationFlow,
    PropertyCheckFlow,
    FPGAXilinxFlow,
    FPGANextPNRFlow,
    FPGAVPRFlow,
    FPGAVPROpenSTAFlow,
    GenerateOpenRCXFlow,
    GeneratePEXEstimateFlow,
    PEXCalibrateFlow,
    HighResScreenshotFlow,
    Img2StreamFlow,
    InterposerFlow,
    LintFlow,
    VerilatorLintFlow,
    SlangLintFlow,
    MagicLVSFlow,
    ShowFlow,
    SignoffFlow,
    SynthesisFlow
])
def test_default_valid(flow: Flowgraph):
    flows = flow.make_docs()
    assert flows
    if not isinstance(flows, list):
        flows = [flows]
    for flow in flows:
        assert flow.validate()


def test_routing_flow_node_order():
    # The route stage mirrors the OpenROAD flow scripts' global route stage: repair
    # the design on global routing parasitics, then repair antennas, then detail
    # route. Pin the chain so an accidental reorder is caught here rather than only
    # showing up as a QoR shift in the nightly EDA survey.
    flow = RoutingFlow()

    expected = {
        "antenna_repair": [("repair_timing", "0")],
        "detailed": [("antenna_repair", "0")],
        "detailed_antenna_repair": [("detailed", "0")],
        "global": [],
        "repair_timing": [("global", "0")],
    }
    assert {step for step, _ in flow.get_nodes()} == set(expected)
    for step, inputs in expected.items():
        assert flow.get_graph_node(step, "0").get_input() == inputs, step

    # Antenna repair on the detailed routes is the last word on routing.
    assert flow.get_exit_nodes() == (("detailed_antenna_repair", "0"),)

    # Each repair node is its own task, not a second instance of an existing one: the
    # schema namespace is keyed on the task name, so sharing it would let two nodes
    # clobber each other's defaults.
    assert flow.get_graph_node("repair_timing", "0").get("task") == "post_route_repair_timing"
    assert flow.get_graph_node("detailed_antenna_repair", "0").get("task") == \
        "detailed_route_antenna_repair"

    # ASICFlow keeps the route.global / route.detailed node names other code and
    # tests key off.
    asic_route = {step for step, _ in ASICFlow().get_nodes() if step.startswith("route.")}
    assert asic_route == {f"route.{step}" for step in expected}


def test_routing_flow_reduction_consumes_the_last_route_node():
    """With np>1 the reduction has to read the end of the chain, not detailed routing.

    Appending a node to the chain without moving the min edge would leave the
    reduction picking the pre-repair database while every per-index chain still looked
    correct, so this pins which node feeds it.
    """
    flow = RoutingFlow("routing", np=3)

    for index in ("0", "1", "2"):
        assert flow.get_graph_node("detailed_antenna_repair", index).get_input() == \
            [("detailed", index)]

    assert flow.get_graph_node("min", "0").get_input() == \
        [("detailed_antenna_repair", index) for index in ("0", "1", "2")]
    assert flow.get_exit_nodes() == (("min", "0"),)


def test_pex_calibrate_flow_structure():
    # PEXCalibrateFlow builds on ASICFlow by dropping the write steps and
    # calibrating on the routed database. It locates that database by the
    # ASICFlow node names ("write.views"/"write.gds"), so a rename in ASICFlow
    # would break construction here. This test pins the invariant so such a
    # rename is caught immediately instead of only in the nightly EDA survey.
    flow = PEXCalibrateFlow()

    # The calibrate node is fed by exactly the node that fed ASICFlow's view
    # write - i.e. the routed database - and not by a write step. Derived from
    # ASICFlow rather than hardcoded so a rename of that node shows up here as a
    # mismatch rather than as a stale literal.
    routed_node = ASICFlow().get_graph_node("write.views", "0").get_input()
    assert len(routed_node) == 1
    calibrate = flow.get_graph_node("calibrate", "0")
    assert calibrate is not None
    assert calibrate.get_input() == routed_node

    # The view/GDS write steps are removed.
    for removed in ("write.views", "write.gds"):
        with pytest.raises(
                ValueError,
                match=rf"^{re.escape(removed)}/0 is not a valid node in pex_calibrate\.$"):
            flow.get_graph_node(removed, "0")
