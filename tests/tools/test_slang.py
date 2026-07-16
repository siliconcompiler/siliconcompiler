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
from siliconcompiler.utils.paths import workdir


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

    # The selected branch is kept and the other pruned; the original default
    # (0) is gone from the declaration.
    assert "module impl_b" in content
    assert "module impl_a" not in content
    assert "MODE = 0" not in content

    # Re-elaborating the emitted file on its own (defaults only, no -G) must
    # succeed without reaching the pruned module -- i.e. no unknown modules --
    # and the baked default must resolve MODE back to 1.
    compilation = _assert_reelaborates_clean(result)
    top_inst = compilation.getRoot().topInstances[0]
    mode = {p.name: p for p in top_inst.body.parameters}["MODE"]
    assert mode.value.value.toString(pyslang.LiteralBase.Decimal, False) == "1"


_TYPED_PARAM_SRC = (
    "package p;\n"
    "  typedef enum logic [1:0] {A = 0, B = 1, C = 2} mode_e;\n"
    "  typedef logic [159:0] wide_t;\n"
    "endpackage\n"
    "module top import p::*; #(\n"
    "  parameter mode_e MODE = A,\n"
    "  parameter wide_t WIDE = 160'h0\n"
    ")(input x, output y);\n"
    "  assign y = x ^ (|WIDE) ^ (MODE == C);\n"
    "endmodule\n"
)


def _elaborate_typed(params):
    """Run the elaborate task on the typed-parameter design with the given
    fileset param overrides ({} for none) and return the output file path."""
    with open("typed.sv", "w") as src:
        src.write(_TYPED_PARAM_SRC)

    design = Design("top")
    design.set_dataroot("typed-test", os.getcwd())
    with design.active_fileset("rtl"), design.active_dataroot("typed-test"):
        design.set_topmodule("top")
        design.add_file("typed.sv")
        for name, value in params.items():
            design.set_param(name, value)

    proj = Project(design)
    proj.add_fileset("rtl")
    flow = Flowgraph("elaborate")
    flow.node("elaborate", elaborate.Elaborate())
    proj.set_flow(flow)
    assert proj.run()

    return proj.find_result("sv", step="elaborate")


def _assert_reelaborates_clean(path):
    """Re-elaborate a standalone file (defaults only), assert no errors, and
    return the resulting compilation for further inspection."""
    driver = pyslang.driver.Driver()
    driver.addStandardArgs()
    opts = pyslang.driver.CommandLineOptions()
    opts.ignoreProgramName = True
    args = shlex.join(["--single-unit", "--top", "top", os.path.abspath(path)])
    assert driver.parseCommandLine(args, opts)
    assert driver.processOptions()
    assert driver.parseAllSources()
    compilation = driver.createCompilation()
    severities = [driver.diagEngine.getSeverity(d.code, d.location)
                  for d in compilation.getAllDiagnostics()]
    assert pyslang.DiagnosticSeverity.Error not in severities
    assert pyslang.DiagnosticSeverity.Fatal not in severities
    return compilation


def test_elaborate_typed_param_overrides_render_valid_sv():
    """Overriding enum- and wide-typedef-typed top parameters must emit valid
    SystemVerilog: enums cast to their type, wide values as full literals.

    This is the ibex-style regression: a bare integer default for an enum
    parameter (or an abbreviated wide literal) does not compile.
    """
    result = _elaborate_typed({"MODE": "C", "WIDE": "160'hdeadbeef"})
    with open(result) as fout:
        content = fout.read()

    # Enum default cast to its declared type; no abbreviated "..." literal.
    assert "mode_e'(" in content
    assert "..." not in content

    # The emitted file re-elaborates standalone (defaults only) without errors,
    # and the baked defaults resolve to the overridden values.
    compilation = _assert_reelaborates_clean(result)
    params = {p.name: p
              for p in compilation.getRoot().topInstances[0].body.parameters}
    assert params["MODE"].value.value.toString(
        pyslang.LiteralBase.Decimal, False) == "2"       # enum value C
    assert params["WIDE"].value.value.toString(
        pyslang.LiteralBase.Hex, True) == "160'hdeadbeef"


def test_elaborate_leaves_untouched_params_verbatim():
    """Typed parameters the fileset did NOT override keep their exact source
    default -- the rewrite never touches them, so it can't mangle enum/typedef
    defaults it wasn't asked to change (the ibex failure mode)."""
    result = _elaborate_typed({})
    with open(result) as fout:
        content = fout.read()

    assert "parameter mode_e MODE = A" in content
    assert "parameter wide_t WIDE = 160'h0" in content
    assert "mode_e'(" not in content


def _build_elaborate(top, filename, source, params=None,
                     source_paths=True, dataroot="cov-test"):
    """Write ``source`` to ``filename`` and return an elaborate-only project."""
    with open(filename, "w") as fout:
        fout.write(source)

    design = Design(top)
    design.set_dataroot(dataroot, os.getcwd())
    with design.active_fileset("rtl"), design.active_dataroot(dataroot):
        design.set_topmodule(top)
        design.add_file(filename)
        for name, value in (params or {}).items():
            design.set_param(name, value)

    proj = Project(design)
    proj.add_fileset("rtl")
    flow = Flowgraph("elaborate")
    flow.node("elaborate", elaborate.Elaborate())
    proj.set_flow(flow)
    if not source_paths:
        elaborate.Elaborate.find_task(proj).set_slang_includesourcepaths(False)
    return proj


def test_elaborate_source_paths_disabled():
    """With include_source_paths off, module text is still emitted but the
    banner / file-annotation comments are omitted entirely."""
    proj = _build_elaborate(
        "top", "nosrc.v",
        "module top(input a, output b); assign b = a; endmodule\n",
        source_paths=False)

    assert proj.run()

    with open(proj.find_result("v", step="elaborate")) as fout:
        content = fout.read()

    assert "module top" in content
    assert "// Start:" not in content
    assert "// End:" not in content
    assert "//   File:" not in content
    assert "////////" not in content


def test_elaborate_errors_on_unrenderable_param():
    """If an overridden top parameter's value cannot be rendered as valid
    SystemVerilog, the task must fail loudly rather than emit a bad default.

    An unpacked-struct parameter elaborates fine but has no simple literal
    form, so overriding it forces the error-out path.
    """
    proj = _build_elaborate(
        "top", "err.sv",
        "package q; typedef struct { int a; int b; } up_t; endpackage\n"
        "module top import q::*; #(parameter up_t P = '{a: 1, b: 2})\n"
        "  (input x, output y);\n"
        "  assign y = x ^ (P.a == 3);\n"
        "endmodule\n",
        params={"P": "'{a: 3, b: 4}"})

    with pytest.raises(RuntimeError):
        proj.run()

    # Confirm it failed for the intended reason (our explicit render error),
    # not an incidental elaboration failure. The message is logged to the node
    # log file -- the RuntimeError itself only carries a generic summary, and
    # the node runs in a separate process so caplog does not see it.
    logtext = ""
    logdir = workdir(proj, step="elaborate", index="0")
    for name in os.listdir(logdir):
        if name.endswith(".log"):
            with open(os.path.join(logdir, name)) as fout:
                logtext += fout.read()
    assert "cannot rewrite the default of top parameter 'P'" in logtext


def test_elaborate_prunes_deep_hierarchy_keeps_interface():
    """Pruning must descend the full hierarchy (grandchildren, interfaces) and
    keep everything reachable while dropping an uninstantiated sibling."""
    proj = _build_elaborate(
        "top", "hier.sv",
        "interface bus_if; logic v; endinterface\n"
        "module leaf(input logic a, output logic b); assign b = ~a; endmodule\n"
        "module mid(bus_if i, output logic o); leaf l(.a(i.v), .b(o)); endmodule\n"
        "module unused(input logic a, output logic b); assign b = a; endmodule\n"
        "module top(output logic o);\n"
        "  bus_if bi();\n"
        "  assign bi.v = 1'b1;\n"
        "  mid m(.i(bi), .o(o));\n"
        "endmodule\n")

    assert proj.run()

    with open(proj.find_result("sv", step="elaborate")) as fout:
        content = fout.read()

    assert "module top" in content
    assert "module mid" in content
    assert "module leaf" in content        # grandchild, reached via mid
    assert "interface bus_if" in content    # instantiated interface
    assert "module unused" not in content   # never instantiated


def test_elaborate_roundtrips_systemverilog_constructs():
    """A design using packages, enums, packed structs and '{...} assignment
    patterns must be emitted so it re-elaborates cleanly -- the ibex-shaped
    regression. Nothing is overridden, so these constructs are verbatim."""
    proj = _build_elaborate(
        "top", "sv_features.sv",
        "package p;\n"
        "  typedef enum logic [1:0] {A = 0, B = 1, C = 2} mode_e;\n"
        "  typedef struct packed { logic irq; logic [4:0] cause; } exc_t;\n"
        "  localparam exc_t ExcSoft = '{irq: 1'b1, cause: 5'd03};\n"
        "endpackage\n"
        "module leaf import p::*; #(parameter mode_e M = A)\n"
        "  (input logic x, output logic y);\n"
        "  assign y = x ^ (M == C) ^ ExcSoft.irq;\n"
        "endmodule\n"
        "module top import p::*; (input logic x, output logic y);\n"
        "  leaf u(.x(x), .y(y));\n"
        "endmodule\n")

    assert proj.run()

    result = proj.find_result("sv", step="elaborate")
    with open(result) as fout:
        content = fout.read()

    # SV constructs preserved verbatim (not down-converted / mangled).
    assert "package p" in content
    assert "'{irq: 1'b1, cause: 5'd03}" in content

    # The emitted file re-elaborates on its own without errors.
    _assert_reelaborates_clean(result)


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


def test_pyslang_driver_parses_verilog():
    """Drive pyslang directly on a tiny verilog file.

    Mirrors the calls made in SlangTask._init_driver / _compile so a regression
    in the underlying pyslang API can be reproduced without any SC plumbing."""
    with open("tiny.v", "w") as src:
        src.write(
            "module tiny(input clk, output reg q);\n"
            "  always @(posedge clk) q <= ~q;\n"
            "endmodule\n"
        )

    driver = pyslang.driver.Driver()
    driver.addStandardArgs()

    opts = pyslang.driver.CommandLineOptions()
    opts.ignoreProgramName = True

    args = shlex.join(["--single-unit", "--top", "tiny", "tiny.v"])
    assert driver.parseCommandLine(args, opts)
    assert driver.processOptions()
    assert driver.parseAllSources()

    compilation = driver.createCompilation()
    diags = compilation.getAllDiagnostics()

    # No errors expected for a well-formed module
    severities = [driver.diagEngine.getSeverity(d.code, d.location) for d in diags]
    assert pyslang.DiagnosticSeverity.Error not in severities
    assert pyslang.DiagnosticSeverity.Fatal not in severities


def test_pyslang_syntax_printer():
    """SyntaxPrinter + Token live in submodules in pyslang v11+."""
    with open("tiny.v", "w") as src:
        src.write("module tiny; endmodule\n")

    driver = pyslang.driver.Driver()
    driver.addStandardArgs()

    opts = pyslang.driver.CommandLineOptions()
    opts.ignoreProgramName = True

    args = shlex.join(["--single-unit", "--top", "tiny", "tiny.v"])
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
