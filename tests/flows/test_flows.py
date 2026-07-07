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
from siliconcompiler.flows.formalflow import FormalFlow
from siliconcompiler.flows.fpgaflow import (
    FPGAXilinxFlow,
    FPGANextPNRFlow,
    FPGAVPRFlow,
    FPGAVPROpenSTAFlow
)
from siliconcompiler.flows.generate_openroad_rcx import GenerateOpenRCXFlow
from siliconcompiler.flows.highresscreenshotflow import HighResScreenshotFlow
from siliconcompiler.flows.img2streamflow import Img2StreamFlow
from siliconcompiler.flows.interposerflow import InterposerFlow
from siliconcompiler.flows.lintflow import LintFlow, VerilatorLintFlow, SlangLintFlow
from siliconcompiler.flows.lvsflow import MagicLVSFlow
from siliconcompiler.flows.showflow import ShowFlow
from siliconcompiler.flows.signoffflow import SignoffFlow
from siliconcompiler.flows.synflow import SynthesisFlow


@pytest.mark.parametrize("flow", [
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
    FormalFlow,
    FPGAXilinxFlow,
    FPGANextPNRFlow,
    FPGAVPRFlow,
    FPGAVPROpenSTAFlow,
    GenerateOpenRCXFlow,
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
