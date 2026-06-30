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
    DFMFlow,
)
from siliconcompiler.flows.drcflow import DRCFlow, KlayoutDRCFlow, MagicDRCFlow
from siliconcompiler.flows.dvflow import (
    DVFlow,
    IcarusDVFlow,
    IcarusCocotbDVFlow,
    VerilatorDVFlow,
    VerilatorCocotbDVFlow,
    XyceDVFlow,
    XDMXyceDVFlow,
)
from siliconcompiler.flows.elaborationflow import (
    ElaborationFlow,
    SV2VElaborationFlow,
    HLSElaborationFlow,
    VHDLElaborationFlow,
    ChiselElaborationFlow,
)
from siliconcompiler.flows.fpgaflow import (
    FPGAXilinxFlow,
    FPGANextPNRFlow,
    FPGAVPRFlow,
    FPGAVPROpenSTAFlow,
)
from siliconcompiler.flows.generate_openroad_rcx import GenerateOpenRCXFlow
from siliconcompiler.flows.highresscreenshotflow import HighResScreenshotFlow
from siliconcompiler.flows.img2streamflow import Img2StreamFlow
from siliconcompiler.flows.interposerflow import InterposerFlow
from siliconcompiler.flows.lintflow import LintFlow, VerilatorLintFlow, SlangLintFlow
from siliconcompiler.flows.lvsflow import MagicLVSFlow
from siliconcompiler.flows.showflow import ShowFlow
from siliconcompiler.flows.signoffflow import SignoffFlow
from siliconcompiler.flows.synflow import (
    SynthesisFlow,
    SV2VSynthesisFlow,
    HLSSynthesisFlow,
    VHDLSynthesisFlow,
    ChiselSynthesisFlow,
)


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
    DFMFlow,
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
    SV2VElaborationFlow,
    HLSElaborationFlow,
    VHDLElaborationFlow,
    ChiselElaborationFlow,
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
    SynthesisFlow,
    SV2VSynthesisFlow,
    HLSSynthesisFlow,
    VHDLSynthesisFlow,
    ChiselSynthesisFlow,
])
def test_default_valid(flow: Flowgraph):
    flows = flow.make_docs()
    assert flows
    if not isinstance(flows, list):
        flows = [flows]
    for flow in flows:
        assert flow.validate()
