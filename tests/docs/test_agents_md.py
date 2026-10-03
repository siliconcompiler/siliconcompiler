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

import ast
import io
import os.path
import re
import tokenize

import pytest
import yaml

import siliconcompiler
from siliconcompiler.schema import docs
# ``tomllib`` is stdlib only from 3.11, and SiliconCompiler supports 3.10, where
# the declared ``tomli`` dependency stands in for it. Reuse the shim the package
# already has rather than repeating the fallback: importing ``tomllib`` directly
# here would be an ImportError at *collection* time on 3.10, failing the whole
# session rather than this file.
from siliconcompiler.utils import tomllib


if not os.path.abspath(__file__).startswith(docs.sc_root):
    pytest.skip(reason="test for docs only possible in editable install",
                allow_module_level=True)


# The shim is None only in a tree where neither stdlib tomllib nor tomli is
# importable. Skip rather than let the tests fail on a NoneType attribute error,
# which says nothing about the cause.
needs_toml = pytest.mark.skipif(
    tomllib is None,
    reason="no TOML reader: Python < 3.11 without the tomli dependency installed")

AGENTS = os.path.join(docs.sc_root, "AGENTS.md")
PREAMBLE = os.path.join(docs.sc_root, "docs", "_llms", "preamble.md")
PYPROJECT = os.path.join(docs.sc_root, "pyproject.toml")
LINT_WORKFLOW = os.path.join(docs.sc_root, ".github", "workflows", "lint.yml")
DOCS_WORKFLOW = os.path.join(docs.sc_root, ".github", "workflows", "docs.yml")

# ``pip install -e .[a,b,c]`` in a shell block, in either file.
PIP_EXTRAS = re.compile(r"pip install\s+(?:-e\s+)?\.\[([a-z0-9,._-]+)\]")


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
    """Every capitalized code span names a current export, so the file cannot outlive a rename."""
    name, text = orientation
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


# Both files introduce their export list with this exact phrase, and the list runs
# to the end of the paragraph. Keeping the wording identical is what lets one test
# check both.
EXPORT_LIST = re.compile(r"Top-level exports, in full:(.*?)\n\s*\n", re.DOTALL)


def test_export_list_is_complete(orientation):
    """The export list says "in full", so it matches ``__all__`` in both directions."""
    name, text = orientation
    match = EXPORT_LIST.search(text)
    assert match, (
        f"{name} no longer contains a paragraph starting 'Top-level exports, in "
        "full:'; this test parses that phrase to find the list")

    listed = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", match.group(1)))
    expected = set(siliconcompiler.__all__)
    assert listed == expected, (
        f"{name}'s export list does not match siliconcompiler.__all__.\n"
        f"  missing from the file: {sorted(expected - listed)}\n"
        f"  no longer exported:    {sorted(listed - expected)}")


def test_removed_symbols_are_still_removed(orientation):
    """The negative claims have to stay true, or they mislead in reverse."""
    name, text = orientation
    assert "Chip" in text, f"{name} should keep warning that Chip is gone"
    for symbol in ("Chip", "ASICProject"):
        assert not hasattr(siliconcompiler, symbol), (
            f"{name} says {symbol} was removed, but it is exported again -- "
            "the file needs updating")


@needs_toml
def test_console_scripts_match_pyproject(orientation):
    """The entry point list is quoted as complete, so it must be."""
    name, text = orientation
    with open(PYPROJECT, "rb") as f:
        declared = set(tomllib.load(f)["project"]["scripts"])

    quoted = set(re.findall(r"`(sc-[a-z]+|smake)`", text))
    assert quoted == declared, (
        f"{name} lists console scripts {sorted(quoted)} but pyproject.toml "
        f"declares {sorted(declared)}")


@needs_toml
def test_no_sc_entry_point():
    """The single most repeated wrong instruction in the project's history."""
    with open(PYPROJECT, "rb") as f:
        scripts = tomllib.load(f)["project"]["scripts"]
    assert "sc" not in scripts, (
        "a bare 'sc' entry point now exists, so AGENTS.md, the llms.txt "
        "preamble and the migration guide all need correcting")


def test_in_tree_module_directories_exist(orientation):
    """The placement policy names four in-tree directories, so check four."""
    name, text = orientation
    for directory in ("tools", "flows", "targets", "checklists"):
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
    """Every lint job in lint.yml is named in AGENTS.md, so a new CI gate cannot go unmentioned."""
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


@needs_toml
def test_install_command_extras_exist(agents):
    """Every extra the install line names has to be declared."""
    match = PIP_EXTRAS.search(agents)
    assert match, "AGENTS.md no longer contains a 'pip install -e .[...]' command"

    with open(PYPROJECT, "rb") as f:
        declared = set(tomllib.load(f)["project"]["optional-dependencies"])

    named = set(match.group(1).split(","))
    assert named <= declared, (
        f"AGENTS.md tells contributors to install extras {sorted(named - declared)}, "
        "which pyproject.toml does not declare")


def test_install_command_covers_the_docs_build(agents):
    """The install line covers every extra docs.yml installs to build the docs."""
    workflow = _read(DOCS_WORKFLOW)
    needed = set()
    for match in PIP_EXTRAS.finditer(workflow):
        needed.update(match.group(1).split(","))
    assert needed, "could not read any 'pip install .[...]' extras out of docs.yml"

    match = PIP_EXTRAS.search(agents)
    assert match, "AGENTS.md no longer contains a 'pip install -e .[...]' command"

    listed = set(match.group(1).split(","))
    assert needed <= listed, (
        f"docs.yml installs extras {sorted(needed - listed)} to build the docs, "
        "which AGENTS.md's install command omits -- following AGENTS.md exactly "
        "would fail the docs build gate")


def test_example_command_is_runnable(orientation):
    """The demo module both files point at has to be importable."""
    name, text = orientation
    assert "siliconcompiler.demos.asic_demo" in text
    module = os.path.join(docs.sc_root, "siliconcompiler", "demos", "asic_demo.py")
    assert os.path.isfile(module), f"{name} points at a demo that does not exist"


def test_named_project_classes_carry_domain_schema():
    """ASIC carries an ``asic`` section and Project and Lint do not, as both files claim."""
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
    """Both files are plain ASCII; the preamble is copied verbatim into llms.txt."""
    name, text = orientation
    offenders = sorted({character for character in text if ord(character) > 127})
    assert not offenders, (
        f"{name} contains non-ASCII characters {offenders}; use \"--\" for a "
        "dash, straight quotes, and \"...\" for an ellipsis")


def _non_ascii_comment_lines(path):
    """Line numbers of the comments and docstrings in ``path`` that are not ASCII."""
    with open(path, encoding="utf-8") as f:
        source = f.read()
    if source.isascii():
        return []

    docstrings = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) \
                and ast.get_docstring(node, clean=False) is not None:
            docstrings.add(node.body[0].lineno)

    return [token.start[0] for token in tokenize.generate_tokens(io.StringIO(source).readline)
            if (token.type == tokenize.COMMENT
                or (token.type == tokenize.STRING and token.start[0] in docstrings))
            and not token.string.isascii()]


def _python_files(*tops):
    """Every ``.py`` file under the given top-level directories of the source tree."""
    for top in tops:
        for dirpath, dirnames, filenames in os.walk(os.path.join(docs.sc_root, top)):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "build", "_build")]
            for name in filenames:
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def test_comments_and_docstrings_are_ascii():
    """AGENTS.md's ASCII rule; strings are exempt for UI text and Unicode test data."""
    offenders = [f"{os.path.relpath(path, docs.sc_root)}:{line}"
                 for path in _python_files("siliconcompiler", "tests", "examples", "scripts",
                                           "docs", "setup", ".github")
                 for line in _non_ascii_comment_lines(path)]
    assert not offenders, (
        "comments and docstrings must be ASCII; use \"--\" for a dash, straight "
        f"quotes, and \"...\" for an ellipsis: {offenders}")


def test_test_docstrings_are_brief():
    """AGENTS.md's cap on test docstrings: no paragraphs, and at most four lines."""
    offenders = []
    for path in _python_files("tests"):
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name.startswith("test_"):
                doc = ast.get_docstring(node)
                if doc and (len(doc.splitlines()) > 4 or "\n\n" in doc):
                    offenders.append(f"{os.path.relpath(path, docs.sc_root)}:{node.lineno}")
    assert not offenders, (
        "a test docstring is at most two sentences saying what the test checks, "
        f"with no blank lines and at most four lines: {offenders}")


# A rule of six or more repeated characters, or a title framed by three or more.
DIVIDER = re.compile(r"^#\s*([-=*#~_])\1{5,}\s*$|^#\s*([-=*#~_])\2{2,}\s+\S.*\s+\2{3,}\s*$")


def test_no_divider_comments():
    """AGENTS.md bans divider and section-heading comments; examples/ is exempt, as the docs
    anchor includes on them."""
    offenders = []
    for path in _python_files("siliconcompiler", "tests"):
        with open(path, encoding="utf-8") as f:
            source = f.read()
        offenders.extend(f"{os.path.relpath(path, docs.sc_root)}:{token.start[0]}"
                         for token in tokenize.generate_tokens(io.StringIO(source).readline)
                         if token.type == tokenize.COMMENT and DIVIDER.match(token.string.strip()))
    assert not offenders, f"divider or section-heading comments: {offenders}"


def test_agents_md_references_resolve(agents):
    """Relative links in AGENTS.md are read on GitHub, where they must resolve."""
    broken = []
    for target in re.findall(r"\]\((?!https?://|#)([^)]+)\)", agents):
        path = os.path.join(docs.sc_root, target.split("#")[0])
        if not os.path.exists(path):
            broken.append(target)
    assert not broken, f"AGENTS.md links to paths that do not exist: {broken}"
