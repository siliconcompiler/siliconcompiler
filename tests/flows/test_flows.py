import pytest

from siliconcompiler.flows.asicflow import ASICFlow, HLSASSICFlow
from siliconcompiler.flows.drcflow import DRCFlow
from siliconcompiler.flows.dvflow import DVFlow
from siliconcompiler.flows.fpgaflow import FPGANextPNRFlow, FPGAVPRFlow, FPGAXilinxFlow
from siliconcompiler.flows.generate_openroad_rcx import GenerateOpenRCXFlow
from siliconcompiler.flows.interposerflow import InterposerFlow
from siliconcompiler.flows.lintflow import LintFlowgraph
from siliconcompiler.flows.showflow import ShowFlow
from siliconcompiler.flows.signoffflow import SignoffFlow
from siliconcompiler.flows.synflow import SynthesisFlowgraph

from siliconcompiler.tools.builtin.nop import NOPTask


@pytest.mark.parametrize("flow", [
    ASICFlow(), HLSASSICFlow(),
    DRCFlow(),
    DVFlow(tool="icarus"), DVFlow(tool="verilator"), DVFlow(tool="xyce"), DVFlow(tool="xdm-xyce"),
    FPGANextPNRFlow(), FPGAVPRFlow(), FPGAXilinxFlow(),
    GenerateOpenRCXFlow(NOPTask()),
    InterposerFlow(),
    LintFlowgraph(tool="slang"), LintFlowgraph(tool="verilator"),
    ShowFlow(NOPTask()),
    SignoffFlow(),
    SynthesisFlowgraph()
])
def test_default_valid(flow: ASICFlow):
    assert flow.validate()
