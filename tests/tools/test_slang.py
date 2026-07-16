import pyslang
import pytest
import re
import shlex

import os.path

from queue import Queue

from siliconcompiler import ASIC
from siliconcompiler import Design
from siliconcompiler import Flowgraph
from siliconcompiler import Project
from siliconcompiler import StdCellLibrary
from siliconcompiler.tools.slang import lint
from siliconcompiler.tools.slang import elaborate
from siliconcompiler.utils.paths import workdir
from siliconcompiler.tools.slang.utils import uniquify
from siliconcompiler.tools.slang.utils import wrapper
from siliconcompiler.tools.slang.utils import macro
from siliconcompiler.tools.slang.utils.uniquify import (
    UniquifyError,
    build_compilation,
    build_compilation_from_design,
    enumerate_module,
    enumerate_modules,
    enumerate_design,
)


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


# ---------------------------------------------------------------------------
# uniquify: enumerate the distinct parameterizations of a module.
#
# Python-only pyslang tests (no full SC run) so they are fast and pinpoint the
# exact pyslang path if the API moves. One test drives the Design-facing wrapper
# against the real heartbeat example.
# ---------------------------------------------------------------------------


_UNIQUIFY_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _uniquify_compile(tmp_path, text, top, **kwargs):
    src = tmp_path / f"{top}.sv"
    src.write_text(text)
    return build_compilation([str(src)], top, **kwargs)


def test_uniquify_single_param_dedup(tmp_path):
    """Four instances, three distinct N -> three variants; N=16 merges."""
    text = """
    module heartbeat #(parameter N = 8) (input clk, input nreset, output reg out);
        reg [N-1:0] c;
        always @(posedge clk) out <= &c;
    endmodule
    module top (input clk, input nreset, output o8, o16, o16b, o32);
        heartbeat #(.N(8))  a (.clk(clk), .nreset(nreset), .out(o8));
        heartbeat #(.N(16)) b (.clk(clk), .nreset(nreset), .out(o16));
        heartbeat #(.N(16)) c (.clk(clk), .nreset(nreset), .out(o16b));
        heartbeat #(.N(32)) d (.clk(clk), .nreset(nreset), .out(o32));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "heartbeat")

    assert [c.params["N"] for c in combos] == [16, 32, 8]  # sorted by signature
    names = {c.name for c in combos}
    assert names == {"heartbeat__N16", "heartbeat__N32", "heartbeat__N8"}

    n16 = next(c for c in combos if c.params["N"] == 16)
    assert n16.instances == ["top.b", "top.c"]


def test_uniquify_multilevel_hierarchy(tmp_path):
    """A target nested two levels deep is found alongside a top-level one."""
    text = """
    module leaf #(parameter int N = 8) (input [N-1:0] din, output [N-1:0] dout);
        assign dout = din;
    endmodule
    module mid #(parameter int W = 4) (input [W-1:0] a, output [W-1:0] b);
        leaf #(.N(W)) u (.din(a), .dout(b));
    endmodule
    module top (input [3:0] x, input [7:0] y, output [3:0] xo, output [7:0] yo);
        mid  #(.W(4)) m4 (.a(x), .b(xo));
        leaf #(.N(8)) l8 (.din(y), .dout(yo));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "leaf")

    paths = sorted(p for c in combos for p in c.instances)
    assert paths == ["top.l8", "top.m4.u"]
    assert {c.params["N"] for c in combos} == {4, 8}


def test_uniquify_ignores_modules_absent_from_elaboration(tmp_path):
    """Only instances in the final elaboration are enumerated.

    A parameterization that lives in a pruned ``generate`` branch, and a module
    that is never instantiated at all, must both be excluded -- otherwise we'd
    generate variants for hardware the design does not actually contain.
    """
    text = """
    module foo #(parameter N = 1) (input a, output b);
        assign b = a;
    endmodule
    module unused (input a, output b);   // never instantiated
        assign b = ~a;
    endmodule
    module top #(parameter USE = 1) (input a, output b, output c);
        if (USE == 0) begin : g_off
            foo #(.N(3)) u_off (.a(a), .b(b));   // pruned (USE defaults to 1)
        end else begin : g_on
            foo #(.N(5)) u_on (.a(a), .b(b));
        end
        foo #(.N(7)) u_always (.a(a), .b(c));
    endmodule
    """
    comp = _uniquify_compile(tmp_path, text, "top")

    # The pruned N=3 branch is excluded; only elaborated instances remain.
    foo = enumerate_module(comp, "foo")
    assert {c.params["N"] for c in foo} == {5, 7}
    assert sorted(p for c in foo for p in c.instances) == \
        ["top.g_on.u_on", "top.u_always"]

    # A module that is never instantiated is not enumerated at all.
    assert enumerate_module(comp, "unused") == []


def test_uniquify_toplevel_parameterized_default(tmp_path):
    """The parameterized top module itself is enumerated (uses its defaults)."""
    text = """
    module heartbeat #(parameter N = 8) (input [N-1:0] d, output [N-1:0] q);
        assign q = d;
    endmodule
    """
    combos = enumerate_module(
        _uniquify_compile(tmp_path, text, "heartbeat"), "heartbeat")

    assert len(combos) == 1
    assert combos[0].params == {"N": 8}
    assert combos[0].name == "heartbeat__N8"
    widths = {p.name: p.width for p in combos[0].ports}
    assert widths == {"d": 8, "q": 8}


def test_uniquify_toplevel_parameterized_override(tmp_path):
    """A -G override on a parameterized top is reflected in the enumeration."""
    text = """
    module heartbeat #(parameter N = 8) (input [N-1:0] d, output [N-1:0] q);
        assign q = d;
    endmodule
    """
    comp = _uniquify_compile(tmp_path, text, "heartbeat", parameters={"N": 20})
    combos = enumerate_module(comp, "heartbeat")

    assert len(combos) == 1
    assert combos[0].params == {"N": 20}
    assert combos[0].name == "heartbeat__N20"
    widths = {p.name: p.width for p in combos[0].ports}
    assert widths == {"d": 20, "q": 20}


def test_uniquify_toplevel_param_propagates_to_child(tmp_path):
    """A top override that flows into a child is captured on that child."""
    text = """
    module leaf #(parameter int N = 8) (input [N-1:0] d, output [N-1:0] q);
        assign q = d;
    endmodule
    module top #(parameter int TOPW = 8) (input [TOPW-1:0] i, output [TOPW-1:0] o);
        leaf #(.N(TOPW)) u (.d(i), .q(o));
    endmodule
    """
    comp = _uniquify_compile(tmp_path, text, "top", parameters={"TOPW": 12})
    leaf = enumerate_module(comp, "leaf")
    assert len(leaf) == 1
    assert leaf[0].params == {"N": 12}
    assert {p.name: p.width for p in leaf[0].ports} == {"d": 12, "q": 12}

    top = enumerate_module(comp, "top")
    assert top[0].params == {"TOPW": 12}
    assert top[0].instances == ["top"]


def test_uniquify_resolved_port_widths(tmp_path):
    """Port widths (including expressions) resolve per parameterization."""
    text = """
    module widthmod #(parameter W = 8) (input [W-1:0] din, output [2*W-1:0] dout);
        assign dout = {din, din};
    endmodule
    module top (input [63:0] i, output [127:0] o);
        widthmod #(.W(8))  a (.din(i[7:0]),  .dout(o[15:0]));
        widthmod #(.W(32)) b (.din(i[31:0]), .dout(o[63:0]));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "widthmod")
    by_w = {c.params["W"]: c for c in combos}

    def widths(c):
        return {p.name: (p.direction, p.width) for p in c.ports}

    assert widths(by_w[8]) == {"din": ("input", 8), "dout": ("output", 16)}
    assert widths(by_w[32]) == {"din": ("input", 32), "dout": ("output", 64)}


def test_uniquify_module_not_found(tmp_path):
    text = "module top (input a, output b); assign b = a; endmodule"
    assert enumerate_module(_uniquify_compile(tmp_path, text, "top"), "nope") == []


def test_uniquify_no_param_module(tmp_path):
    """A module with no overridable parameters yields one bare-named combo."""
    text = """
    module leaf (input a, output b); assign b = a; endmodule
    module top (input a, output b);
        leaf u (.a(a), .b(b));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "leaf")
    assert len(combos) == 1
    assert combos[0].params == {}
    assert combos[0].name == "leaf"


def test_uniquify_string_param_literal(tmp_path):
    """Short, identifier-safe string params appear literally in the name."""
    text = """
    module leaf #(parameter string MODE = "fast") (input a, output b);
        assign b = a;
    endmodule
    module top (input a, output b0, output b1);
        leaf #(.MODE("fast")) u0 (.a(a), .b(b0));
        leaf #(.MODE("slow")) u1 (.a(a), .b(b1));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "leaf")
    names = {c.params["MODE"]: c.name for c in combos}
    assert names == {"fast": "leaf__MODEfast", "slow": "leaf__MODEslow"}


def test_uniquify_string_param_illegal_chars_hashed(tmp_path):
    """Strings with illegal identifier characters are hashed, not literal."""
    text = """
    module leaf #(parameter string MODE = "x") (input a, output b);
        assign b = a;
    endmodule
    module top (input a, output b0, output b1);
        leaf #(.MODE("a/b:c")) u0 (.a(a), .b(b0));
        leaf #(.MODE("d.e-f")) u1 (.a(a), .b(b1));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "leaf")
    for c in combos:
        assert _UNIQUIFY_IDENT.match(c.name), f"illegal name: {c.name}"
        assert "/" not in c.name and ":" not in c.name and "." not in c.name
    assert len({c.name for c in combos}) == 2


def test_uniquify_long_string_hashed(tmp_path):
    """Strings longer than the literal limit are hashed."""
    long_a = "a" * 40
    long_b = "b" * 40
    text = f"""
    module leaf #(parameter string MODE = "x") (input a, output b);
        assign b = a;
    endmodule
    module top (input a, output b0, output b1);
        leaf #(.MODE("{long_a}")) u0 (.a(a), .b(b0));
        leaf #(.MODE("{long_b}")) u1 (.a(a), .b(b1));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "leaf")
    for c in combos:
        assert _UNIQUIFY_IDENT.match(c.name)
        assert len(c.name) <= 64
        assert long_a not in c.name and long_b not in c.name
    assert len({c.name for c in combos}) == 2


def test_uniquify_negative_param(tmp_path):
    text = """
    module leaf #(parameter int OFF = 0) (input a, output b);
        assign b = a;
    endmodule
    module top (input a, output b0, output b1);
        leaf #(.OFF(-5)) u0 (.a(a), .b(b0));
        leaf #(.OFF(7))  u1 (.a(a), .b(b1));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "leaf")
    names = {c.params["OFF"]: c.name for c in combos}
    assert names == {-5: "leaf__OFFn5", 7: "leaf__OFF7"}
    for name in names.values():
        assert _UNIQUIFY_IDENT.match(name)


def test_uniquify_multi_param_naming_sorted(tmp_path):
    """Multiple parameters are ordered deterministically (sorted by name)."""
    text = """
    module leaf #(parameter int N = 8, parameter string MODE = "x")
                 (input [N-1:0] d, output [N-1:0] q);
        assign q = d;
    endmodule
    module top (input [15:0] i, output [15:0] o);
        leaf #(.N(16), .MODE("go")) u (.d(i), .q(o));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "leaf")
    assert combos[0].name == "leaf__MODEgo__N16"


def test_uniquify_determinism(tmp_path):
    text = """
    module leaf #(parameter int N = 8) (input [N-1:0] d, output [N-1:0] q);
        assign q = d;
    endmodule
    module top (input [31:0] i, output [31:0] o);
        leaf #(.N(8))  a (.d(i[7:0]),  .q(o[7:0]));
        leaf #(.N(32)) b (.d(i),       .q(o));
    endmodule
    """
    comp = _uniquify_compile(tmp_path, text, "top")
    first = [(c.name, c.params) for c in enumerate_module(comp, "leaf")]
    comp2 = _uniquify_compile(tmp_path, text, "top")
    second = [(c.name, c.params) for c in enumerate_module(comp2, "leaf")]
    assert first == second


def test_uniquify_names_unique_and_valid(tmp_path):
    text = """
    module leaf #(parameter int N = 8, parameter string MODE = "x")
                 (input [N-1:0] d, output [N-1:0] q);
        assign q = d;
    endmodule
    module top (input [63:0] i, output [63:0] o);
        leaf #(.N(8),  .MODE("a"))       u0 (.d(i[7:0]),  .q(o[7:0]));
        leaf #(.N(8),  .MODE("bad/one"))  u1 (.d(i[7:0]),  .q(o[7:0]));
        leaf #(.N(16), .MODE("a"))       u2 (.d(i[15:0]), .q(o[15:0]));
        leaf #(.N(32), .MODE("a"))       u3 (.d(i),       .q(o));
    endmodule
    """
    combos = enumerate_module(_uniquify_compile(tmp_path, text, "top"), "leaf")
    names = [c.name for c in combos]
    assert len(names) == 4
    assert len(set(names)) == 4
    assert all(_UNIQUIFY_IDENT.match(n) for n in names)


def test_uniquify_hash_fallback_on_length():
    """A name that would exceed max_len falls back to the signature hash."""
    param = uniquify.Parameterization("mod", {"NAME": "a" * 8}, [])
    uniquify.assign_variant_names([param], max_len=8)
    assert param.name.startswith("mod__")
    assert _UNIQUIFY_IDENT.match(param.name)


def test_uniquify_signature_distinguishes_int_and_string():
    int_param = uniquify.Parameterization("m", {"P": 8}, [])
    str_param = uniquify.Parameterization("m", {"P": "8"}, [])
    assert int_param.signature != str_param.signature


def test_uniquify_elaboration_error_raises(tmp_path):
    src = tmp_path / "bad.sv"
    src.write_text("module top (input a); undefined_thing u (); endmodule\n")
    with pytest.raises(UniquifyError):
        build_compilation([str(src)], "top")


def test_uniquify_enumerate_design_heartbeat(heartbeat_design):
    """The Design wrapper pulls sources/params from a real SC Design."""
    Project(heartbeat_design)  # ensures the fileset resolves like a real run
    combos = enumerate_design(heartbeat_design, "heartbeat", fileset="rtl")
    assert len(combos) == 1
    assert combos[0].params == {"N": 8}
    assert combos[0].name == "heartbeat__N8"
    ports = {p.name: p.direction for p in combos[0].ports}
    assert ports == {"clk": "input", "nreset": "input", "out": "output"}


# ---------------------------------------------------------------------------
# wrapper: generate the parameterized wrapper + param-less variants.
#
# The generated SystemVerilog is round-tripped back through slang to prove it
# elaborates and dispatches correctly, rather than string-matching the output.
# ---------------------------------------------------------------------------


_WRAPPER_HEARTBEAT = """
module heartbeat #(parameter N = 8, parameter string MODE = "fast") (
    input      clk,
    input      nreset,
    output reg [N-1:0] out
);
    always @(posedge clk) out <= out + 1'b1;
endmodule
"""

_WRAPPER_TOP = _WRAPPER_HEARTBEAT + """
module top (input clk, input nreset,
            output [7:0] a, output [15:0] b, output [15:0] c);
    heartbeat #(.N(8),  .MODE("fast")) u0 (.clk(clk), .nreset(nreset), .out(a));
    heartbeat #(.N(16), .MODE("slow")) u1 (.clk(clk), .nreset(nreset), .out(b));
    heartbeat #(.N(16), .MODE("slow")) u2 (.clk(clk), .nreset(nreset), .out(c));
endmodule
"""


def _wrapper_generate(tmp_path):
    src = tmp_path / "top.sv"
    src.write_text(_WRAPPER_TOP)
    comp = build_compilation([str(src)], "top")
    combos = enumerate_module(comp, "heartbeat")
    return comp, combos, wrapper.generate_uniquified(comp, "heartbeat", combos=combos)


def _wrapper_stub(combo):
    """A blackbox module standing in for a hardened macro."""
    decls = ",\n    ".join(
        (f"{p.direction} {p.name}" if p.width == 1
         else f"{p.direction} [{p.width - 1}:0] {p.name}")
        for p in combo.ports)
    return f"module {combo.name} (\n    {decls}\n);\nendmodule\n"


def test_wrapper_generate_shape(tmp_path):
    """generate_uniquified returns a wrapper and one variant per combo."""
    _, combos, gen = _wrapper_generate(tmp_path)
    assert set(gen["variants"]) == {c.name for c in combos}
    assert gen["wrapper"].startswith("module heartbeat")
    # The wrapper preserves the original parameterized port width...
    assert "[N-1:0] out" in gen["wrapper"]
    # ...but ports must be nets: the original `output reg out` is driven by the
    # variant instance, which is illegal for a variable in plain Verilog.
    assert "output reg" not in gen["wrapper"]
    assert "reg [N-1:0] out" not in gen["wrapper"]


def test_wrapper_ports_forced_to_nets(tmp_path):
    """reg/logic/var qualifiers are stripped from wrapper ports (nets only)."""
    text = """
    module m #(parameter N = 4) (
        input logic clk,
        output reg [N-1:0] a,
        output logic [N-1:0] b,
        output var c
    );
        always_comb a = '0;
        assign b = '0;
        always_comb c = 1'b0;
    endmodule
    module top (input clk, output [3:0] a, output [3:0] b, output c);
        m #(.N(4)) u (.clk(clk), .a(a), .b(b), .c(c));
    endmodule
    """
    src = tmp_path / "top.sv"
    src.write_text(text)
    header = wrapper.get_module_header(build_compilation([str(src)], "top"), "m")
    # No variable data type survives on any port declaration.
    for bad in ("output reg", "output logic", "output var", "input logic"):
        assert bad not in header
    # Widths are preserved.
    assert "[N-1:0] a" in header and "[N-1:0] b" in header


def test_wrapper_variant_roundtrip(tmp_path):
    """Each variant is a baked copy of the module -- no inner instance."""
    _, combos, gen = _wrapper_generate(tmp_path)

    by_name = {c.name: c for c in combos}
    for name, text in gen["variants"].items():
        # The variant is the renamed module, not a shell around it.
        assert text.startswith(f"module {name}")
        assert "u_impl" not in text

        vfile = tmp_path / f"{name}.sv"
        vfile.write_text(text)
        # It elaborates standalone (no dependency on the original module) with
        # the concrete parameters baked into its own definition.
        comp = build_compilation([str(vfile)], name)
        inner = [i for i in uniquify.iter_instances(comp)
                 if i.definition.name == "heartbeat"]
        assert inner == []
        top = comp.getRoot().topInstances[0]
        got = {p.name: p.value for p in top.body.parameters}
        assert int(str(got["N"])) == by_name[name].params["N"]
        assert str(got["MODE"]).strip('"') == by_name[name].params["MODE"]


def test_wrapper_dispatch_roundtrip(tmp_path):
    """A parent driving the wrapper selects the matching variant per instance."""
    _, combos, gen = _wrapper_generate(tmp_path)

    (tmp_path / "wrap.sv").write_text(gen["wrapper"])
    (tmp_path / "stubs.sv").write_text("".join(_wrapper_stub(c) for c in combos))
    (tmp_path / "parent.sv").write_text("""
    module parent (input clk, input nreset, output [7:0] a, output [15:0] b);
        heartbeat #(.N(8),  .MODE("fast")) i0 (.clk(clk), .nreset(nreset), .out(a));
        heartbeat #(.N(16), .MODE("slow")) i1 (.clk(clk), .nreset(nreset), .out(b));
    endmodule
    """)

    comp = build_compilation(
        [str(tmp_path / "parent.sv"), str(tmp_path / "wrap.sv"),
         str(tmp_path / "stubs.sv")], "parent")

    selected = {}
    for inst in uniquify.iter_instances(comp):
        if inst.definition.name.startswith("heartbeat__"):
            parent_inst = inst.hierarchicalPath.split(".")[1]
            selected[parent_inst] = inst.definition.name

    assert selected == {
        "i0": "heartbeat__MODEfast__N8",
        "i1": "heartbeat__MODEslow__N16",
    }


def test_wrapper_unhardened_param_errors(tmp_path):
    """Instantiating the wrapper with an unhardened combo triggers $error."""
    _, combos, gen = _wrapper_generate(tmp_path)
    (tmp_path / "wrap.sv").write_text(gen["wrapper"])
    (tmp_path / "stubs.sv").write_text("".join(_wrapper_stub(c) for c in combos))
    (tmp_path / "parent.sv").write_text("""
    module parent (input clk, input nreset, output [3:0] z);
        heartbeat #(.N(99), .MODE("fast")) i (.clk(clk), .nreset(nreset), .out(z));
    endmodule
    """)
    with pytest.raises(UniquifyError, match="no hardened variant"):
        build_compilation(
            [str(tmp_path / "parent.sv"), str(tmp_path / "wrap.sv"),
             str(tmp_path / "stubs.sv")], "parent")


def test_wrapper_no_params_raises(tmp_path):
    text = """
    module leaf (input a, output b); assign b = a; endmodule
    module top (input a, output b); leaf u (.a(a), .b(b)); endmodule
    """
    src = tmp_path / "top.sv"
    src.write_text(text)
    comp = build_compilation([str(src)], "top")
    with pytest.raises(UniquifyError, match="no parameters"):
        wrapper.generate_uniquified(comp, "leaf")


def test_wrapper_module_not_found_raises(tmp_path):
    src = tmp_path / "top.sv"
    src.write_text("module top (input a, output b); assign b = a; endmodule")
    comp = build_compilation([str(src)], "top")
    with pytest.raises(UniquifyError, match="not instantiated"):
        wrapper.generate_uniquified(comp, "nope")


def test_wrapper_format_param_value():
    assert wrapper.format_param_value(8) == "8"
    assert wrapper.format_param_value(-3) == "-3"
    assert wrapper.format_param_value(True) == "1"
    assert wrapper.format_param_value("fast") == '"fast"'
    assert wrapper.format_param_value('a"b') == '"a\\"b"'


def test_wrapper_header_strips_leading_comment(tmp_path):
    """A file banner comment before the module is not carried into the wrapper."""
    text = """// file banner mentioning the module word
    // second banner line
    module leaf #(parameter int N = 8) (input [N-1:0] d, output [N-1:0] q);
        assign q = d;
    endmodule
    module top (input [7:0] i, output [7:0] o);
        leaf #(.N(8)) u (.d(i), .q(o));
    endmodule
    """
    src = tmp_path / "top.sv"
    src.write_text(text)
    comp = build_compilation([str(src)], "top")
    header = wrapper.get_module_header(comp, "leaf")
    assert header.startswith("module leaf")
    assert "banner" not in header


def test_uniquify_toplevel_no_default_param_errors(tmp_path):
    """A parameterized top with no default cannot elaborate; error gives a hint."""
    text = """
    module leaf #(parameter int N = 8) (input [N-1:0] d, output [N-1:0] q);
        assign q = d;
    endmodule
    module top #(parameter int TOPW) (input [TOPW-1:0] i, output [TOPW-1:0] o);
        leaf #(.N(TOPW)) u (.d(i), .q(o));
    endmodule
    """
    src = tmp_path / "top.sv"
    src.write_text(text)
    with pytest.raises(UniquifyError, match="parameter without a default"):
        build_compilation([str(src)], "top")

    # Supplying the value lets it elaborate and propagate to the child.
    comp = build_compilation([str(src)], "top", parameters={"TOPW": 10})
    combos = enumerate_module(comp, "leaf")
    assert combos[0].params == {"N": 10}


_MULTI_MODULE = """
module leaf #(parameter int N = 8) (input [N-1:0] d, output [N-1:0] q);
    assign q = d;
endmodule
module gizmo #(parameter int W = 2) (input [W-1:0] a, output [W-1:0] b);
    assign b = ~a;
endmodule
module top (input [63:0] i, output [63:0] o);
    leaf  #(.N(8))  la (.d(i[7:0]),  .q(o[7:0]));
    leaf  #(.N(16)) lb (.d(i[15:0]), .q(o[15:0]));
    gizmo #(.W(4))  ga (.a(i[3:0]),  .b(o[19:16]));
    gizmo #(.W(4))  gb (.a(i[7:4]),  .b(o[23:20]));
endmodule
"""


def test_uniquify_enumerate_multiple_modules(tmp_path):
    """One pass enumerates several module names; names never cross-collide."""
    comp = _uniquify_compile(tmp_path, _MULTI_MODULE, "top")
    result = enumerate_modules(comp, ["leaf", "gizmo"])

    assert set(result) == {"leaf", "gizmo"}
    assert {c.name for c in result["leaf"]} == {"leaf__N8", "leaf__N16"}
    # gizmo's two W=4 instances merge into one variant.
    assert {c.name for c in result["gizmo"]} == {"gizmo__W4"}
    assert result["gizmo"][0].instances == ["top.ga", "top.gb"]


def test_uniquify_enumerate_modules_preserves_order_and_missing(tmp_path):
    comp = _uniquify_compile(tmp_path, _MULTI_MODULE, "top")
    result = enumerate_modules(comp, ["gizmo", "absent", "leaf"])
    assert list(result) == ["gizmo", "absent", "leaf"]
    assert result["absent"] == []


def test_wrapper_generate_multiple_modules(tmp_path):
    """generate_modules returns wrapper + variants for each requested module."""
    comp = _uniquify_compile(tmp_path, _MULTI_MODULE, "top")
    generated = wrapper.generate_modules(comp, ["leaf", "gizmo"])

    assert set(generated) == {"leaf", "gizmo"}
    assert set(generated["leaf"]["variants"]) == {"leaf__N8", "leaf__N16"}
    assert generated["leaf"]["wrapper"].startswith("module leaf")
    assert set(generated["gizmo"]["variants"]) == {"gizmo__W4"}
    assert generated["gizmo"]["wrapper"].startswith("module gizmo")


def test_enumerate_design_accepts_list(heartbeat_design):
    """enumerate_design returns a dict when given a list of module names."""
    Project(heartbeat_design)
    result = enumerate_design(heartbeat_design, ["heartbeat"], fileset="rtl")
    assert set(result) == {"heartbeat"}
    assert result["heartbeat"][0].name == "heartbeat__N8"
    # A single string still returns a bare list.
    single = enumerate_design(heartbeat_design, "heartbeat", fileset="rtl")
    assert single[0].name == "heartbeat__N8"


# ---------------------------------------------------------------------------
# macro: build wrapper/variant designs and wire them into a parent (alias).
# ---------------------------------------------------------------------------


_HIER_HEARTBEAT = (
    "module heartbeat #(parameter N = 8) "
    "(input clk, input nreset, output reg out);\n"
    "    reg [N-1:0] c;\n"
    "    always @(posedge clk) out <= &c;\n"
    "endmodule\n"
)
_HIER_TOP = (
    "module top (input clk, input nreset, output a, output b, output c);\n"
    "    heartbeat #(.N(8))  u0 (.clk(clk), .nreset(nreset), .out(a));\n"
    "    heartbeat #(.N(16)) u1 (.clk(clk), .nreset(nreset), .out(b));\n"
    "    heartbeat #(.N(16)) u2 (.clk(clk), .nreset(nreset), .out(c));\n"
    "endmodule\n"
)


def _hier_designs(tmp_path):
    """A `top` design depending on `heartbeat` in a separate fileset/design."""
    (tmp_path / "heartbeat.v").write_text(_HIER_HEARTBEAT)
    (tmp_path / "top.v").write_text(_HIER_TOP)

    heartbeat = Design("heartbeat")
    heartbeat.set_dataroot("root", str(tmp_path))
    with heartbeat.active_fileset("rtl"), heartbeat.active_dataroot("root"):
        heartbeat.set_topmodule("heartbeat")
        heartbeat.add_file("heartbeat.v")

    top = Design("top")
    top.set_dataroot("root", str(tmp_path))
    with top.active_fileset("rtl"), top.active_dataroot("root"):
        top.set_topmodule("top")
        top.add_file("top.v")
        top.add_depfileset(heartbeat, depfileset="rtl", fileset="rtl")
    return top, heartbeat


def test_build_compilation_from_design_resolves_deps(tmp_path):
    """A module defined in a dependency fileset is found via the parent design."""
    top, _ = _hier_designs(tmp_path)
    combos = enumerate_module(build_compilation_from_design(top), "heartbeat")
    assert {c.name for c in combos} == {"heartbeat__N8", "heartbeat__N16"}
    n16 = next(c for c in combos if c.params["N"] == 16)
    assert n16.instances == ["top.u1", "top.u2"]


def test_uniquified_setup_adds_filesets(tmp_path):
    """Construction enumerates + generates and registers the new filesets."""
    top, _ = _hier_designs(tmp_path)
    uq = macro.Uniquified(top, ["heartbeat"], libdir=str(tmp_path / "uq"))

    assert uq.variants == {"heartbeat": ["heartbeat__N16", "heartbeat__N8"]}
    assert set(uq.variant_names) == {"heartbeat__N8", "heartbeat__N16"}
    assert uq.wrapper_filesets == {
        "heartbeat": "rtl.heartbeat.wrapper", "all": "rtl.wrapper"}
    assert uq.hardened_filesets == {
        "heartbeat__N8": "rtl.hardened.heartbeat__N8",
        "heartbeat__N16": "rtl.hardened.heartbeat__N16"}

    # Filesets are registered on the design...
    for fileset in ("rtl.heartbeat.wrapper", "rtl.wrapper",
                    "rtl.hardened.heartbeat__N8", "rtl.hardened.heartbeat__N16"):
        assert fileset in top.getkeys("fileset")
    assert top.get_topmodule(fileset="rtl.heartbeat.wrapper") == "heartbeat"
    # ...but construction writes nothing to disk.
    assert not os.path.exists(os.path.join(uq.outdir, "heartbeat.wrapper.v"))


def test_uniquified_write_materializes_sources(tmp_path):
    """Sources are written only when write() (or build/wireup) is called."""
    top, _ = _hier_designs(tmp_path)
    uq = macro.Uniquified(top, ["heartbeat"], libdir=str(tmp_path / "uq"))

    assert not os.path.isdir(str(tmp_path / "uq"))  # nothing on disk yet

    uq.write()
    assert os.path.exists(os.path.join(uq.outdir, "heartbeat.wrapper.v"))
    for variant in uq.variant_names:
        assert os.path.exists(os.path.join(uq.outdir, f"{variant}.v"))


def test_uniquified_hardened_fileset_resolves_original(tmp_path):
    """The hardening fileset elaborates the baked variant as its own top."""
    top, _ = _hier_designs(tmp_path)
    macro.Uniquified(top, ["heartbeat"],
                     libdir=str(tmp_path / "uq")).write()  # register + materialize

    comp = build_compilation_from_design(top, "rtl.hardened.heartbeat__N16")
    # The variant is the top and has N baked in; the original parameterized
    # `heartbeat` is present but uninstantiated (so not iterated).
    top_inst = comp.getRoot().topInstances[0]
    assert top_inst.name == "heartbeat__N16"
    params = {p.name: p.value for p in top_inst.body.parameters}
    assert int(str(params["N"])) == 16
    assert not [i for i in uniquify.iter_instances(comp)
                if i.definition.name == "heartbeat"]


def test_uniquified_select(tmp_path):
    """Target selection: all / by module / by variant glob."""
    top, _ = _hier_designs(tmp_path)
    uq = macro.Uniquified(top, ["heartbeat"], libdir=str(tmp_path / "uq"))

    assert set(uq._select(None)) == {"heartbeat__N8", "heartbeat__N16"}
    assert set(uq._select("heartbeat")) == {"heartbeat__N8", "heartbeat__N16"}
    assert uq._select("heartbeat__N16") == ["heartbeat__N16"]
    assert uq._select("*N8") == ["heartbeat__N8"]
    with pytest.raises(UniquifyError):
        uq._select("nope*")


def test_uniquified_instance_path(tmp_path):
    """The wrapper->variant hierarchy path is derivable from the class."""
    top, _ = _hier_designs(tmp_path)
    uq = macro.Uniquified(top, ["heartbeat"], libdir=str(tmp_path / "uq"))

    inst = wrapper.DEFAULT_INSTANCE_NAME
    assert uq.instance_path("heartbeat__N8") == f"g_heartbeat__N8/{inst}"
    assert uq.instance_path("heartbeat__N8", parent="tb/DUT") == \
        f"tb/DUT/g_heartbeat__N8/{inst}"
    with pytest.raises(UniquifyError, match="unknown variant"):
        uq.instance_path("heartbeat__N999")


def _leaf_designs(tmp_path):
    """A `top` depending on an unparameterized `leaf` module."""
    (tmp_path / "leaf.v").write_text(
        "module leaf (input a, output b);\n    assign b = ~a;\nendmodule\n")
    (tmp_path / "leaftop.v").write_text(
        "module leaftop (input x, output y);\n"
        "    leaf u0 (.a(x), .b(y));\n"
        "endmodule\n")

    leaf = Design("leaf")
    leaf.set_dataroot("root", str(tmp_path))
    with leaf.active_fileset("rtl"), leaf.active_dataroot("root"):
        leaf.set_topmodule("leaf")
        leaf.add_file("leaf.v")

    top = Design("leaftop")
    top.set_dataroot("root", str(tmp_path))
    with top.active_fileset("rtl"), top.active_dataroot("root"):
        top.set_topmodule("leaftop")
        top.add_file("leaftop.v")
        top.add_depfileset(leaf, depfileset="rtl", fileset="rtl")
    return top, leaf


def test_uniquified_unparameterized_module(tmp_path):
    """An unparameterized module is hardened directly: no wrapper, no variant src."""
    top, leaf = _leaf_designs(tmp_path)
    uq = macro.Uniquified(top, ["leaf"], libdir=str(tmp_path / "uq"))

    # One variant, named after the module (no parameter suffix).
    assert uq.variants == {"leaf": ["leaf"]}
    # No wrapper is generated for it.
    assert uq.wrapper_filesets == {}
    assert uq.hardened_filesets == {"leaf": "rtl.hardened.leaf"}

    # write() produces no source for it (nothing to generate).
    uq.write()
    assert not os.path.exists(os.path.join(uq.outdir, "leaf.wrapper.v"))
    assert not os.path.exists(os.path.join(uq.outdir, "leaf.v"))

    # The hardened fileset re-points at the original module's RTL.
    comp = build_compilation_from_design(top, "rtl.hardened.leaf")
    tops = [i.name for i in comp.getRoot().topInstances]
    assert tops == ["leaf"]

    # instance_path is meaningless without a wrapper.
    with pytest.raises(UniquifyError, match="unparameterized"):
        uq.instance_path("leaf")


def test_uniquified_unparameterized_wireup_blackboxes(tmp_path):
    """wireup blackboxes an unparameterized module and injects its macro."""
    top, leaf = _leaf_designs(tmp_path)
    libdir = tmp_path / "uq"
    uq = macro.Uniquified(top, ["leaf"], libdir=str(libdir))

    # Seed a cached macro so no EDA is needed.
    (libdir).mkdir(parents=True, exist_ok=True)
    StdCellLibrary("leaf").write_manifest(str(libdir / "leaf.json"))
    uq.load_macros()

    project = ASIC(top)
    project.add_fileset("rtl")
    uq.wireup(project)

    # Blackbox alias: leaf.rtl -> (nothing).
    aliases = [tuple(a) for a in project.get("option", "alias")]
    assert ("leaf", "rtl", None, None) in aliases
    assert "leaf" in project.get("asic", "asiclib")


def test_uniquified_module_not_a_dependency(tmp_path):
    """A module that is not a resolvable dependency errors clearly."""
    top, _ = _hier_designs(tmp_path)
    with pytest.raises(UniquifyError, match="not the top of any resolved fileset"):
        macro.Uniquified(top, ["ghost"], libdir=str(tmp_path / "uq"))


def test_uniquified_build_cache_then_wireup(tmp_path):
    """Cached macros load without EDA; wireup aliases + injects them."""
    top, _ = _hier_designs(tmp_path)
    libdir = tmp_path / "macros"
    libdir.mkdir()
    uq = macro.Uniquified(top, ["heartbeat"], libdir=str(libdir))

    # Seed cached macros (as a prior build would have) so no EDA is needed.
    for variant in uq.variant_names:
        StdCellLibrary(variant).write_manifest(str(libdir / f"{variant}.json"))

    built = uq.build(target=None)
    assert set(built) == set(uq.variant_names)

    project = ASIC(top)
    project.add_fileset("rtl")
    uq.wireup(project)

    aliases = [tuple(a) for a in project.get("option", "alias")]
    assert ("heartbeat", "rtl", "top", "rtl.heartbeat.wrapper") in aliases
    asiclibs = project.get("asic", "asiclib")
    for variant in uq.variant_names:
        assert variant in asiclibs


def test_uniquified_wireup_requires_built_macros(tmp_path):
    """wireup refuses to run if a used variant has no macro."""
    top, _ = _hier_designs(tmp_path)
    uq = macro.Uniquified(top, ["heartbeat"], libdir=str(tmp_path / "uq"))
    project = ASIC(top)
    project.add_fileset("rtl")
    with pytest.raises(UniquifyError, match="run build"):
        uq.wireup(project)


def test_macro_corners_from_project_scenarios(asic_heartbeat):
    """build_macro derives corners from the project's timing scenarios.

    freepdk45 defines a single 'typical' scenario, so a macro built from it must
    not require the skywater130 'slow'/'typical'/'fast' set. This asserts the
    keypath build_macro reads (:keypath:`constraint,timing,scenario`) matches
    the per-corner ``.lib`` files write.views emits.
    """
    corners = asic_heartbeat.getkeys("constraint", "timing", "scenario")
    assert list(corners) == ["typical"]
