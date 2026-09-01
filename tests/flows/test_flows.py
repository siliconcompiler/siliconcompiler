import pytest

import re

from siliconcompiler import Flowgraph, Design, Project
from siliconcompiler.asic import ASIC
from siliconcompiler.targets._utils import detect_elaboration_language

from siliconcompiler.flows.asicflow import (
    ASICFlow,
    SV2VASICFlow,
    HLSASICFlow,
    VHDLASICFlow,
    ChiselASICFlow,
    SODAASICFlow,
    PNRFlow,
    CleanupSynthFlow,
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
from siliconcompiler.flows.formalflow import PropertyCheckFlow, LECFlow
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
from siliconcompiler.flows.sodaflow import (
    SODABaselineElaborationFlow,
    SODAOptimizedElaborationFlow,
    SODATransformedElaborationFlow
)
from siliconcompiler.flows.synflow import SynthesisFlow


@pytest.fixture
def make_project():
    """Builds a project whose design has a single fileset containing one file
    for each requested filetype.

    The files are declared relative to a dataroot and never touch disk;
    ``detect_elaboration_language`` only checks for the presence of a filetype, not
    the file contents.
    """
    def _make_project(*filetypes, project_cls=Project, name="test", fileset="rtl"):
        design = Design(name)
        design.set_dataroot("testdata", __file__)
        with design.active_dataroot("testdata"), design.active_fileset(fileset):
            design.set_topmodule("top")
            for idx, filetype in enumerate(filetypes):
                design.add_file(f"src{idx}.dat", filetype=filetype)
        proj = project_cls(design)
        proj.add_fileset(fileset)
        return proj
    return _make_project


@pytest.mark.parametrize("flow", [
    CheckLibraryFlow,
    ASICFlow,
    SV2VASICFlow,
    HLSASICFlow,
    VHDLASICFlow,
    ChiselASICFlow,
    SODAASICFlow,
    PNRFlow,
    CleanupSynthFlow,
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
    SODABaselineElaborationFlow,
    SODAOptimizedElaborationFlow,
    SODATransformedElaborationFlow,
    PropertyCheckFlow,
    LECFlow,
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


def test_equivalence_flow_holds_only_the_check():
    # This flow holds the equivalence check and nothing else, whichever tool and
    # check it is built for: the views it compares are built by whichever flow it
    # is grafted onto, so a front end added here would be a second copy of what
    # the caller already runs.
    for flow in LECFlow.make_docs():
        assert flow.get_nodes() == (("lec", "0"),)
        assert flow.get_graph_node("lec", "0").get_input() == []


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


@pytest.mark.parametrize("filetype,expected", [
    ("verilog", "verilog"),
    ("systemverilog", "systemverilog"),
    ("vhdl", "vhdl"),
    ("c", "hls"),
    ("bsv", "bluespec"),
    ("chisel", "chisel"),
    ("scala", "chisel"),
])
def test_detect_elaboration_language_single(make_project, filetype, expected):
    proj = make_project(filetype)
    assert detect_elaboration_language(proj) == expected


@pytest.mark.parametrize("filetypes,expected", [
    (("verilog", "chisel"), "chisel"),
    (("verilog", "scala"), "chisel"),
    (("verilog", "vhdl"), "vhdl"),
    (("verilog", "c"), "hls"),
    (("verilog", "bsv"), "bluespec"),
    (("systemverilog", "verilog"), "systemverilog"),
])
def test_detect_elaboration_language_precedence(make_project, filetypes, expected):
    # When a single fileset holds more than one language, the higher-precedence
    # language wins regardless of the order the files were added.
    proj = make_project(*filetypes)
    assert detect_elaboration_language(proj) == expected


def test_detect_elaboration_language_asic_project(make_project):
    # The helper works for ASIC projects, not just the base Project.
    proj = make_project("vhdl", project_cls=ASIC)
    assert detect_elaboration_language(proj) == "vhdl"


def test_detect_elaboration_language_unknown_filetype_returns_default(make_project):
    # A fileset with only non-HDL files falls back to the default.
    proj = make_project("lef")
    assert detect_elaboration_language(proj) == "verilog"


def test_detect_elaboration_language_custom_default(make_project):
    proj = make_project("lef")
    assert detect_elaboration_language(proj, default="systemverilog") == "systemverilog"


def test_detect_elaboration_language_multiple_filesets():
    # The first fileset with a detectable language wins.
    design = Design("multi")
    design.set_dataroot("testdata", __file__)
    with design.active_dataroot("testdata"):
        with design.active_fileset("rtl"):
            design.set_topmodule("top")
            design.add_file("top.vhd", filetype="vhdl")
        with design.active_fileset("extra"):
            design.set_topmodule("top")
            design.add_file("extra.v", filetype="verilog")
    proj = Project(design)
    proj.add_fileset("rtl")
    proj.add_fileset("extra")
    assert detect_elaboration_language(proj) == "vhdl"


# ---------------------------------------------------------------------------
# Incomplete / malformed project setups: detection must never raise, it should
# always fall back to the (possibly customized) default language.
# ---------------------------------------------------------------------------

def test_detect_elaboration_language_no_design():
    # An empty project has no design name set.
    assert detect_elaboration_language(Project()) == "verilog"


def test_detect_elaboration_language_no_design_custom_default():
    assert detect_elaboration_language(Project(), default="vhdl") == "vhdl"


def test_detect_elaboration_language_design_name_not_loaded():
    # Design name is set but the design was never loaded as a library.
    proj = Project()
    proj.set_design("ghost")
    assert detect_elaboration_language(proj) == "verilog"


def test_detect_elaboration_language_no_filesets():
    # A design exists but no filesets are selected on the project.
    assert detect_elaboration_language(Project(Design("empty"))) == "verilog"


def test_detect_elaboration_language_empty_fileset():
    # A fileset is selected but contains no files.
    design = Design("nofiles")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = Project(design)
    proj.add_fileset("rtl")
    assert detect_elaboration_language(proj) == "verilog"


def test_detect_elaboration_language_empty_fileset_custom_default():
    design = Design("nofiles")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = Project(design)
    proj.add_fileset("rtl")
    assert detect_elaboration_language(proj, default="chisel") == "chisel"


# ``frontend`` is how a front end this module knows nothing about takes the place
# of the language-specific subflows, so what is pinned here is that it reaches
# all three levels of the composition and that nothing about the language path
# changed.


@pytest.mark.parametrize("flowcls", [ElaborationFlow, SynthesisFlow, ASICFlow])
def test_frontend_replaces_the_language_subflow(flowcls):
    flow = flowcls(frontend=SODAOptimizedElaborationFlow())

    steps = {step for step, _ in flow.get_nodes()}
    # The SODA front end's nodes, in place of slang's single "elaborate".
    assert {"tosa2linalg", "bufferize", "soda", "translate", "runtime", "link",
            "convert"}.issubset(steps)
    assert "elaborate" not in steps
    assert flow.validate()


@pytest.mark.parametrize("flowcls,prefix", [
    (ElaborationFlow, "elaborationflow"),
    (SynthesisFlow, "synflow"),
    (ASICFlow, "asicflow")
])
def test_frontend_names_the_flow_after_itself(flowcls, prefix):
    # The default name has to say which front end is in the flow, the way it
    # says which language otherwise.
    assert flowcls(frontend=SODABaselineElaborationFlow()).name == \
        f"{prefix}-sodabaselineelaborationflow"
    assert flowcls(language="vhdl").name == f"{prefix}-vhdl"


@pytest.mark.parametrize("flowcls", [ElaborationFlow, SynthesisFlow, ASICFlow])
def test_frontend_wins_over_language(flowcls):
    # language keeps its default, so it cannot be told apart from an explicit
    # one; the front end is what was asked for, so it is what is built.
    flow = flowcls(language="vhdl", frontend=SODABaselineElaborationFlow())
    assert "ghdl" not in {step for step, _ in flow.get_nodes()}
    assert "soda" in {step for step, _ in flow.get_nodes()}


def test_frontend_must_be_a_flowgraph():
    with pytest.raises(ValueError, match="frontend must be a Flowgraph"):
        ElaborationFlow(frontend=SODABaselineElaborationFlow)


def test_soda_asic_flow_resolves_the_strategy():
    for strategy, task in (("baseline", "baseline"),
                           ("optimized", "optimized"),
                           ("transformed", "transformed")):
        flow = SODAASICFlow(strategy=strategy)
        assert flow.get_graph_node("soda", "0").get_task() == task

    with pytest.raises(ValueError, match="Unsupported SODA strategy: nope"):
        SODAASICFlow(strategy="nope")
