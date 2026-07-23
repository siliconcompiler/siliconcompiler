import pytest

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


def test_pex_calibrate_flow_structure():
    # PEXCalibrateFlow builds on ASICFlow by dropping the write steps and
    # calibrating on the routed database. It locates that database by the
    # ASICFlow node names ("write.views"/"write.gds"), so a rename in ASICFlow
    # would break construction here. This test pins the invariant so such a
    # rename is caught immediately instead of only in the nightly EDA survey.
    flow = PEXCalibrateFlow()

    # The calibrate node exists and is fed by the routed database (a single
    # upstream node), not by a write step.
    calibrate = flow.get_graph_node("calibrate", "0")
    assert calibrate is not None
    inputs = calibrate.get_input()
    assert len(inputs) == 1

    # The view/GDS write steps are removed.
    for removed in ("write.views", "write.gds"):
        with pytest.raises(ValueError):
            flow.get_graph_node(removed, "0")
