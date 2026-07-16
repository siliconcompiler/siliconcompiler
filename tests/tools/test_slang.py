import pyslang
import pytest
import shlex

import os.path

from queue import Queue

from siliconcompiler import Design
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


def test_elaborate_drops_unused_modules():
    """Only the top module and the submodules it instantiates should be
    written to the elaborated output; unused modules present in the sources
    must be dropped, while packages are always retained.

    The unused module lives in its own file, so this also verifies that the
    emitted source-path annotations only reference files that actually
    contributed a module to the output."""
    with open("used.v", "w") as src:
        src.write(
            "package pkg; parameter W = 1; endpackage\n"
            "module used_child(input a, output b); assign b = ~a; endmodule\n"
            "module top(input x, output y);\n"
            "  used_child u0(.a(x), .b(y));\n"
            "endmodule\n"
        )
    with open("unused.v", "w") as src:
        src.write(
            "module unused_child(input a, output b); assign b = a; endmodule\n"
        )

    design = Design("top")
    design.set_dataroot("unused-test", os.getcwd())
    with design.active_fileset("rtl"), design.active_dataroot("unused-test"):
        design.set_topmodule("top")
        design.add_file("used.v")
        design.add_file("unused.v")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("elaborate")
    flow.node("elaborate", elaborate.Elaborate())
    proj.set_flow(flow)

    assert proj.run()

    result = proj.find_result("v", step="elaborate")
    with open(result) as fout:
        content = fout.read()

    # Only reachable modules (and packages) are emitted.
    assert "module top" in content
    assert "module used_child" in content
    assert "package pkg" in content
    assert "module unused_child" not in content

    # The file that only held the dropped module must not be annotated.
    assert "used.v" in content
    assert "unused.v" not in content


def test_elaborate_bakes_top_param_overrides():
    """The emitted top module advertises the parameters it was elaborated with.

    ``top`` selects a submodule via ``generate`` on parameter ``MODE``. The
    fileset overrides ``MODE`` to 1 (so ``impl_b`` is used and ``impl_a`` is
    pruned). Because the top is emitted with ``MODE``'s default rewritten to 1,
    re-elaborating the output file standalone -- with only its own defaults --
    reproduces the same hierarchy instead of reaching the pruned ``impl_a``.
    """
    with open("design.sv", "w") as src:
        src.write(
            "module impl_a(input x, output y); assign y = x; endmodule\n"
            "module impl_b(input x, output y); assign y = ~x; endmodule\n"
            "module top #(parameter integer MODE = 0)(input x, output y);\n"
            "  if (MODE == 0) begin : g\n"
            "    impl_a u(.x(x), .y(y));\n"
            "  end else begin : g\n"
            "    impl_b u(.x(x), .y(y));\n"
            "  end\n"
            "endmodule\n"
        )

    design = Design("top")
    design.set_dataroot("param-test", os.getcwd())
    with design.active_fileset("rtl"), design.active_dataroot("param-test"):
        design.set_topmodule("top")
        design.add_file("design.sv")
        design.set_param("MODE", "1")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("elaborate")
    flow.node("elaborate", elaborate.Elaborate())
    proj.set_flow(flow)

    assert proj.run()

    result = proj.find_result("sv", step="elaborate")
    with open(result) as fout:
        content = fout.read()

    # Default baked to the elaborated value; the selected branch kept, the
    # other pruned.
    assert "MODE = 1" in content
    assert "MODE = 0" not in content
    assert "module impl_b" in content
    assert "module impl_a" not in content

    # Re-elaborating the emitted file on its own (defaults only, no -G) must
    # succeed without reaching the pruned module -- i.e. no unknown modules.
    driver = pyslang.driver.Driver()
    driver.addStandardArgs()
    opts = pyslang.driver.CommandLineOptions()
    opts.ignoreProgramName = True
    args = shlex.join(["--single-unit", "--top", "top", os.path.abspath(result)])
    assert driver.parseCommandLine(args, opts)
    assert driver.processOptions()
    assert driver.parseAllSources()
    compilation = driver.createCompilation()
    severities = [driver.diagEngine.getSeverity(d.code, d.location)
                  for d in compilation.getAllDiagnostics()]
    assert pyslang.DiagnosticSeverity.Error not in severities
    assert pyslang.DiagnosticSeverity.Fatal not in severities


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
