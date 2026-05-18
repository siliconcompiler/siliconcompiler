import pyslang
import pytest
import shlex

import os.path

from siliconcompiler import Flowgraph
from siliconcompiler import Project
from siliconcompiler.tools.slang import lint
from siliconcompiler.tools.slang import elaborate


@pytest.mark.parametrize("task", [elaborate.Elaborate, lint.Lint])
def test_version_fail(task, monkeypatch):
    class Version(pyslang.VersionInfo):
        @staticmethod
        def getMajor():
            return 8

        @staticmethod
        def getMinor():
            return 9

        @staticmethod
        def getPatch():
            return 10

    monkeypatch.setattr(pyslang, "VersionInfo", Version)
    with pytest.raises(RuntimeError, match=r"^incorrect pyslang version: 8.9.10$"):
        task()


@pytest.mark.parametrize("task", [elaborate.Elaborate, lint.Lint])
def test_version_pass(task):
    assert task()


def test_lint(heartbeat_design):
    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("lint")
    flow.node("lint", lint.Lint())
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='lint', index='0') == 0
    assert proj.history("job0").get('metric', 'warnings', step='lint', index='0') == 0


def test_elaborate(heartbeat_design):
    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("elaborate")
    flow.node("elaborate", elaborate.Elaborate())
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='elaborate', index='0') == 0
    assert proj.history("job0").get('metric', 'warnings', step='elaborate', index='0') == 0

    assert proj.find_result("v", step="elaborate") == \
        os.path.abspath("build/heartbeat/job0/elaborate/0/outputs/heartbeat.v")


def test_slang_duplicate_inputs(heartbeat_design):
    heartbeat_design.copy_fileset("rtl", "rtl_double")
    heartbeat_design.add_file(heartbeat_design.get_file("rtl", "verilog"), "rtl_double")

    proj = Project(heartbeat_design)
    proj.add_fileset("rtl_double")

    flow = Flowgraph("lint")
    flow.node("lint", lint.Lint())
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='lint', index='0') == 0
    assert proj.history("job0").get('metric', 'warnings', step='lint', index='0') == 0


# ---------------------------------------------------------------------------
# Python-only tests for the pyslang interface used by the slang tool.
#
# These tests directly exercise the pyslang API paths referenced by
# siliconcompiler.tools.slang. They do not run a full SC project, which makes
# them fast and easy to debug when pyslang reorganizes its modules. If pyslang
# moves a symbol again, these tests pinpoint the exact attribute path that
# broke.
# ---------------------------------------------------------------------------


def test_pyslang_api_surface():
    """Verify every pyslang attribute path used by the slang tool resolves.

    When pyslang reorganizes its package layout (as in the v10 -> v11 move
    of Driver/CommandLineOptions/SyntaxPrinter/Token into submodules), this
    test fails fast with a clear pointer to the missing path."""
    assert pyslang.VersionInfo is not None
    assert pyslang.Diags is not None
    assert pyslang.DiagnosticSeverity.Ignored is not None
    assert pyslang.DiagnosticSeverity.Warning is not None
    assert pyslang.DiagnosticSeverity.Error is not None
    assert pyslang.DiagnosticSeverity.Fatal is not None

    assert pyslang.driver.Driver is not None
    assert pyslang.driver.CommandLineOptions is not None

    assert pyslang.syntax.SyntaxPrinter is not None
    assert pyslang.parsing.Token is not None

    # Diagnostic codes referenced by elaborate.py
    for diag in ("MissingTimeScale", "UsedBeforeDeclared", "UnusedParameter",
                 "UnusedDefinition", "UnusedVariable", "UnusedPort",
                 "UnusedButSetNet", "UnusedImplicitNet", "UnusedButSetVariable",
                 "UnusedButSetPort", "UnusedTypedef", "UnusedGenvar",
                 "UnusedAssertionDecl"):
        assert hasattr(pyslang.Diags, diag), f"pyslang.Diags missing: {diag}"


def test_pyslang_driver_parses_verilog(tmp_path):
    """Drive pyslang directly on a tiny verilog file.

    Mirrors the calls made in SlangTask._init_driver / _compile so a regression
    in the underlying pyslang API can be reproduced without any SC plumbing."""
    src = tmp_path / "tiny.v"
    src.write_text(
        "module tiny(input clk, output reg q);\n"
        "  always @(posedge clk) q <= ~q;\n"
        "endmodule\n"
    )

    driver = pyslang.driver.Driver()
    driver.addStandardArgs()

    opts = pyslang.driver.CommandLineOptions()
    opts.ignoreProgramName = True

    args = shlex.join(["--single-unit", "--top", "tiny", str(src)])
    assert driver.parseCommandLine(args, opts)
    assert driver.processOptions()
    assert driver.parseAllSources()

    compilation = driver.createCompilation()
    diags = compilation.getAllDiagnostics()

    # No errors expected for a well-formed module
    severities = [driver.diagEngine.getSeverity(d.code, d.location) for d in diags]
    assert pyslang.DiagnosticSeverity.Error not in severities
    assert pyslang.DiagnosticSeverity.Fatal not in severities


def test_pyslang_syntax_printer(tmp_path):
    """SyntaxPrinter + Token live in submodules in pyslang v11+."""
    src = tmp_path / "tiny.v"
    src.write_text("module tiny; endmodule\n")

    driver = pyslang.driver.Driver()
    driver.addStandardArgs()

    opts = pyslang.driver.CommandLineOptions()
    opts.ignoreProgramName = True

    args = shlex.join(["--single-unit", "--top", "tiny", str(src)])
    assert driver.parseCommandLine(args, opts)
    assert driver.processOptions()
    assert driver.parseAllSources()

    compilation = driver.createCompilation()
    trees = compilation.getSyntaxTrees()
    assert trees

    writer = pyslang.syntax.SyntaxPrinter(compilation.sourceManager)
    writer.setIncludeMissing(False)
    writer.setIncludeDirectives(False)
    text = writer.print(trees[0]).str()
    assert "module" in text
    assert "tiny" in text

    # Walk the syntax tree the same way elaborate.py does and assert we
    # actually identify Tokens through pyslang.parsing.Token. If pyslang
    # moves Token again, this fails with a clear isinstance miss.
    from queue import Queue
    nodes = Queue()
    nodes.put(trees[0].root)
    found_token = False
    while not nodes.empty():
        node = nodes.get()
        for child in node:
            if isinstance(child, pyslang.parsing.Token):
                found_token = True
            else:
                nodes.put(child)
    assert found_token
