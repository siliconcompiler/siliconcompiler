"""Check the claims ``AGENTS.md`` and the llms.txt preamble make about the code.

Both files exist to tell a reader -- usually a code assistant -- which API is
current and which names no longer exist. That makes them the two documents in the
repository with the most to lose from going stale: a confidently-worded, wrong
orientation file is worse than none, because it will be believed.

Neither can be generated, because the useful part is editorial. So instead of
generating them, this asserts the mechanically checkable claims: that the symbols
they name exist, that the ones they say are gone are gone, that the console
scripts they list match ``pyproject.toml``, and that the lint gates they tell a
contributor to run match the ones CI actually runs.
"""

import os.path
import re
import tomllib

import pytest
import yaml

import siliconcompiler
from siliconcompiler.schema import docs


if not os.path.abspath(__file__).startswith(docs.sc_root):
    pytest.skip(reason="test for docs only possible in editable install",
                allow_module_level=True)


AGENTS = os.path.join(docs.sc_root, "AGENTS.md")
PREAMBLE = os.path.join(docs.sc_root, "docs", "_llms", "preamble.md")
PYPROJECT = os.path.join(docs.sc_root, "pyproject.toml")
LINT_WORKFLOW = os.path.join(docs.sc_root, ".github", "workflows", "lint.yml")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def agents():
    return _read(AGENTS)


@pytest.fixture
def preamble():
    return _read(PREAMBLE)


@pytest.fixture(params=[AGENTS, PREAMBLE], ids=["AGENTS.md", "llms_preamble"])
def orientation(request):
    """Both orientation files, checked against the same claims."""
    return os.path.relpath(request.param, docs.sc_root), _read(request.param)


def test_exported_symbols_exist(orientation):
    """Every ``siliconcompiler.X`` name presented as current must import.

    The failure this guards against is the file outliving a rename, which is
    exactly what happened to the class names it is warning the reader about.
    """
    name, text = orientation
    # The full export list both files quote, as a comma-separated run of
    # backticked names.
    quoted = set(re.findall(r"`([A-Z][A-Za-z]+)`", text))
    # Names the files quote as *removed* are expected to be absent.
    removed = {"Chip", "ASICProject", "Library", "LibrarySchema", "Flow",
               "FlowgraphSchema", "DesignSchema", "PDKSchema", "ASICSchema",
               "MetricSchema", "Schema", "SiliconCompilerError"}
    missing = sorted(symbol for symbol in quoted - removed
                     if not hasattr(siliconcompiler, symbol))
    assert not missing, (
        f"{name} names symbols that are not exported from siliconcompiler: "
        f"{missing}")


def test_removed_symbols_are_still_removed(orientation):
    """The negative claims have to stay true, or they mislead in reverse."""
    name, text = orientation
    assert "Chip" in text, f"{name} should keep warning that Chip is gone"
    for symbol in ("Chip", "ASICProject"):
        assert not hasattr(siliconcompiler, symbol), (
            f"{name} says {symbol} was removed, but it is exported again -- "
            "the file needs updating")


def test_console_scripts_match_pyproject(orientation):
    """The entry point list is quoted as complete, so it must be."""
    name, text = orientation
    with open(PYPROJECT, "rb") as f:
        declared = set(tomllib.load(f)["project"]["scripts"])

    quoted = set(re.findall(r"`(sc-[a-z]+|smake)`", text))
    assert quoted == declared, (
        f"{name} lists console scripts {sorted(quoted)} but pyproject.toml "
        f"declares {sorted(declared)}")


def test_no_sc_entry_point():
    """The single most repeated wrong instruction in the project's history."""
    with open(PYPROJECT, "rb") as f:
        scripts = tomllib.load(f)["project"]["scripts"]
    assert "sc" not in scripts, (
        "a bare 'sc' entry point now exists, so AGENTS.md, the llms.txt "
        "preamble and the migration guide all need correcting")


def test_in_tree_module_directories_exist(orientation):
    """The placement policy names four in-tree directories."""
    name, text = orientation
    for directory in ("tools", "flows", "targets"):
        assert f"`{directory}/`" in text or f"siliconcompiler/{directory}" in text, \
            f"{name} no longer mentions siliconcompiler/{directory}/"
        assert os.path.isdir(os.path.join(docs.sc_root, "siliconcompiler", directory))


def test_directories_it_says_do_not_exist(orientation):
    """``siliconcompiler/pdks/`` and ``libs/`` are the stale-guide trap."""
    name, _ = orientation
    for directory in ("pdks", "libs"):
        assert not os.path.isdir(os.path.join(docs.sc_root, "siliconcompiler",
                                              directory)), \
            (f"siliconcompiler/{directory}/ now exists, but {name} tells readers "
             "it does not -- the placement policy changed")


def test_lint_gates_match_ci(agents):
    """AGENTS.md claims four lint gates; CI is the authority on how many.

    Contributors and agents fail the gates they do not know about, which is the
    whole reason the list is in the file. A fifth job landing in CI without a
    line here recreates that gap.
    """
    with open(LINT_WORKFLOW, encoding="utf-8") as f:
        jobs = list(yaml.safe_load(f)["jobs"])
    assert jobs, "could not read job names out of lint.yml"

    tools = {"lint_python": "flake8", "lint_tcl": "tclint", "spelling": "codespell",
             "lint_verilog": "verible-verilog-lint"}
    unknown = sorted(set(jobs) - set(tools))
    assert not unknown, (
        f"lint.yml has new jobs {unknown}; add them to AGENTS.md and "
        "CONTRIBUTING.md, then to the mapping in this test")

    for job in jobs:
        assert tools[job] in agents, (
            f"CI runs the {job} gate with {tools[job]}, which AGENTS.md does "
            "not mention")


def test_example_command_is_runnable(orientation):
    """The demo module both files point at has to be importable."""
    name, text = orientation
    assert "siliconcompiler.demos.asic_demo" in text
    module = os.path.join(docs.sc_root, "siliconcompiler", "demos", "asic_demo.py")
    assert os.path.isfile(module), f"{name} points at a demo that does not exist"


def test_named_project_classes_carry_domain_schema():
    """The reason both files say to prefer the named classes over ``Project``.

    The advice is only worth giving while it is true: a named class exists to
    bring its domain's parameters, and the base class deliberately has none of
    them. If ``Project`` ever grew an ``asic`` section the guidance would need
    rewording.
    """
    from siliconcompiler import ASIC, Design, Lint, Project

    design = Design("t")
    design.set_topmodule("t", fileset="rtl")

    assert "asic" in ASIC(design).getkeys(), \
        "ASIC no longer carries an 'asic' schema section"
    for cls in (Project, Lint):
        instance = cls(design) if cls is not Project else cls()
        assert "asic" not in instance.getkeys(), (
            f"{cls.__name__} now carries an 'asic' section, so the advice to "
            "prefer the named project classes needs rewording")


def test_orientation_files_are_ascii(orientation):
    """Keep these two plain ASCII.

    The preamble is copied verbatim into ``llms.txt`` and ``llms-full.txt``, which
    are plain-text files people grep, diff and paste snippets out of. A curly
    apostrophe next to code is a small trap for no benefit, and the same argument
    applies to ``AGENTS.md``. The llms.txt generator strips the typographic
    characters Sphinx introduces; nothing strips the ones an author types, so
    they are rejected here instead.
    """
    name, text = orientation
    offenders = sorted({character for character in text if ord(character) > 127})
    assert not offenders, (
        f"{name} contains non-ASCII characters {offenders}; use \"--\" for a "
        "dash, straight quotes, and \"...\" for an ellipsis")


def test_agents_md_references_resolve(agents):
    """Relative links in AGENTS.md are read on GitHub, where they must resolve."""
    broken = []
    for target in re.findall(r"\]\((?!https?://|#)([^)]+)\)", agents):
        path = os.path.join(docs.sc_root, target.split("#")[0])
        if not os.path.exists(path):
            broken.append(target)
    assert not broken, f"AGENTS.md links to paths that do not exist: {broken}"
