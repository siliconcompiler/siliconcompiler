import pytest
from siliconcompiler.targets import \
    asap7_demo, freepdk45_demo, \
    gf180_demo, ihp130_demo, interposer_demo, skywater130_demo
from siliconcompiler.targets._utils import detect_elaboration_language

from siliconcompiler import ASIC, Project, Design


@pytest.mark.parametrize("target", (
        asap7_demo,
        freepdk45_demo,
        gf180_demo,
        ihp130_demo,
        interposer_demo,
        skywater130_demo))
def test_target_loading_asic(target):
    proj = ASIC()
    target(proj)

    assert len(proj.getkeys('library')) != 0
    assert proj.get("asic", "mainlib") is not None
    assert proj._has_library(proj.get("asic", "mainlib")) is True

    assert proj.get("asic", "asiclib") is not None

    assert proj.get("asic", "pdk") is not None
    assert proj._has_library(proj.get("asic", "pdk")) is True

    assert proj.get("option", "flow") is not None
    assert proj.get("option", "flow") in proj.getkeys("flowgraph")


def _make_project(*filetypes, fileset="rtl", name="testdesign", project_cls=Project):
    """Builds a project whose design has a single fileset containing one file
    for each requested filetype.

    The file paths are absolute and never touch disk; ``detect_elaboration_language``
    only checks for the presence of a filetype, not the file contents.
    """
    design = Design(name)
    with design.active_fileset(fileset):
        design.set_topmodule("top")
        for idx, filetype in enumerate(filetypes):
            design.add_file(f"/fake/path/src{idx}.dat", filetype=filetype)
    proj = project_cls(design)
    proj.add_fileset(fileset)
    return proj


@pytest.mark.parametrize("filetype,expected", [
    ("verilog", "verilog"),
    ("systemverilog", "systemverilog"),
    ("vhdl", "vhdl"),
    ("c", "hls"),
    ("bsv", "bluespec"),
    ("chisel", "chisel"),
    ("scala", "chisel"),
])
def test_detect_elaboration_language_single(filetype, expected):
    proj = _make_project(filetype)
    assert detect_elaboration_language(proj) == expected


@pytest.mark.parametrize("filetypes,expected", [
    (("verilog", "chisel"), "chisel"),
    (("verilog", "scala"), "chisel"),
    (("verilog", "vhdl"), "vhdl"),
    (("verilog", "c"), "hls"),
    (("verilog", "bsv"), "bluespec"),
    (("systemverilog", "verilog"), "verilog"),
])
def test_detect_elaboration_language_precedence(filetypes, expected):
    # When a single fileset holds more than one language, the higher-precedence
    # language wins regardless of the order the files were added.
    proj = _make_project(*filetypes)
    assert detect_elaboration_language(proj) == expected


def test_detect_elaboration_language_asic_project():
    # The helper works for ASIC projects, not just the base Project.
    proj = _make_project("vhdl", project_cls=ASIC)
    assert detect_elaboration_language(proj) == "vhdl"


def test_detect_elaboration_language_unknown_filetype_returns_default():
    # A fileset with only non-HDL files falls back to the default.
    proj = _make_project("lef")
    assert detect_elaboration_language(proj) == "verilog"


def test_detect_elaboration_language_custom_default():
    proj = _make_project("lef")
    assert detect_elaboration_language(proj, default="systemverilog") == "systemverilog"


def test_detect_elaboration_language_multiple_filesets():
    # The first fileset with a detectable language wins.
    design = Design("multi")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_file("/fake/path/top.vhd", filetype="vhdl")
    with design.active_fileset("extra"):
        design.set_topmodule("top")
        design.add_file("/fake/path/extra.v", filetype="verilog")
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
