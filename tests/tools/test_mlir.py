import pathlib
import pytest

import os.path

from siliconcompiler import Design, Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.mlir import MLIRTask, render_pipeline_options
from siliconcompiler.tools.mlir.compile import RuntimeTask
from siliconcompiler.tools.mlir.link import LinkTask
from siliconcompiler.tools.mlir.opt import (
    OptTask, BufferizeTask, LinalgToLLVMTask, PassesTask, PipelineTask, TosaToLinalgTask)
from siliconcompiler.tools.mlir.translate import TranslateTask


@pytest.fixture
def mm_design(datadir):
    """A TOSA module whose entry function is ``forward``, so the kernel that
    soda-opt outlines from it -- and the topmodule -- is ``forward_kernel``."""
    design = Design("mm")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("forward_kernel")
        design.add_file("mm.mlir")
    return design


def _node(design, task, step="convert"):
    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node(step, task)
    proj.set_flow(flow)

    return SchedulerNode(proj, step, "0")


def _setup_upstream(proj, *steps):
    """Sets up the named nodes, as the scheduler does before running any of them.

    A node's outputs are declared by its own setup(), so a downstream node only
    sees what an upstream will hand it once that upstream has been set up.
    """
    for step in steps:
        node = SchedulerNode(proj, step, "0")
        with node.runtime():
            assert node.setup() is True


def test_mlir_filetype():
    """.mlir resolves to the 'mlir' filetype the MLIR tasks look for."""
    from siliconcompiler.utils import get_default_iomap
    assert get_default_iomap()["mlir"] == "mlir"


def test_parse_version():
    task = TosaToLinalgTask()
    assert task.parse_version(
        "LLVM (http://llvm.org/):\n"
        "  LLVM version 19.1.5\n"
        "  Optimized build.\n"
        "  Default target: x86_64-unknown-linux-gnu\n") == "19.1.5"


def test_parse_version_clang():
    task = RuntimeTask()
    assert task.parse_version("clang version 19.1.5\nTarget: x86_64\n") == "19.1.5"
    assert task.parse_version("Ubuntu clang version 16.0.6 (15)") == "16.0.6"


def test_render_pipeline_options():
    # None drops the option, True emits the bare flag, anything else is a value.
    assert render_pipeline_options([
        ("dropped", None),
        ("flag", True),
        ("count", 3),
    ]) == "flag count=3"
    assert render_pipeline_options([("dropped", None)]) == ""


def test_tosa2linalg_runtime_opts(mm_design, datadir):
    node = _node(mm_design, TosaToLinalgTask(), step="tosa2linalg")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert arguments == [
        "-pass-pipeline=builtin.module(func.func(tosa-to-arith, tosa-to-tensor, "
        "tosa-to-linalg-named, tosa-to-linalg))",
        os.path.join(datadir, "mm.mlir"),
        "-o", os.path.join("outputs", "forward_kernel.mlir"),
    ]


def test_bufferize_runtime_opts(mm_design):
    node = _node(mm_design, BufferizeTask(), step="bufferize")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    # A pass list, not a -pass-pipeline: mlir-opt rejects a command line
    # carrying both, so the two forms must never appear together.
    assert not any(arg.startswith("-pass-pipeline") for arg in arguments)
    assert "-one-shot-bufferize=function-boundary-type-conversion=identity-layout-map " \
           "bufferize-function-boundaries allow-return-allocs-from-loops " \
           "unknown-type-conversion=identity-layout-map" in arguments
    assert arguments[-2:] == ["-o", os.path.join("outputs", "forward_kernel.mlir")]


def test_the_two_pass_forms_cannot_be_combined():
    """mlir-opt takes -pass-pipeline or individual passes, never both, so a task
    carries one form or the other and the combination is unrepresentable."""
    pipeline = TosaToLinalgTask()
    assert pipeline.valid("var", "pipeline")
    assert not pipeline.valid("var", "passes")
    assert not hasattr(pipeline, "add_mlir_passes")

    passes = BufferizeTask()
    assert passes.valid("var", "passes")
    assert not passes.valid("var", "pipeline")
    assert not hasattr(passes, "set_mlir_pipeline")


def test_opt_task_is_abstract():
    """The shared base has no pass form, so it cannot be a node on its own."""
    task = OptTask()
    with pytest.raises(NotImplementedError, match="pass-form specific"):
        task._pass_options()


def test_empty_pipeline(mm_design):
    """A task with nothing to run does not reach mlir-opt: 'pipeline' is a
    required key, so the run stops at validation."""
    node = _node(mm_design, PipelineTask(), step="opt")
    with node.runtime():
        assert node.setup() is True
        assert "var,pipeline" in ",".join(node.task.get("require"))
        assert node.validate() is False


def test_empty_passes(mm_design):
    """Same for the pass-list form -- an empty list is no value at all."""
    node = _node(mm_design, PassesTask(), step="opt")
    with node.runtime():
        assert node.setup() is True
        assert "var,passes" in ",".join(node.task.get("require"))
        assert node.validate() is False


def test_passes_setter():
    task = LinalgToLLVMTask()
    assert task.get("var", "passes") == task._passes

    task.add_mlir_passes(["-cse"], clobber=True)
    assert task.get("var", "passes") == ["-cse"]

    task.add_mlir_passes("-canonicalize")
    assert task.get("var", "passes") == ["-cse", "-canonicalize"]

    task.add_mlir_passes("-symbol-dce", clobber=True)
    assert task.get("var", "passes") == ["-symbol-dce"]


def test_pipeline_setter():
    task = TosaToLinalgTask()
    assert task.get("var", "pipeline") == task._pipeline

    task.set_mlir_pipeline("builtin.module(canonicalize)")
    assert task.get("var", "pipeline") == "builtin.module(canonicalize)"


def test_plugin_setters(mm_design, datadir):
    """Passes and dialects are separate entry points in mlir-opt, so they are
    separate parameters; both load before the passes they provide are named."""
    node = _node(mm_design, TosaToLinalgTask(), step="opt")

    plugin = os.path.join(datadir, "mm.mlir")  # any existing file resolves
    task = TosaToLinalgTask.find_task(node.project)
    task.add_mlir_passplugin(plugin)
    task.add_mlir_dialectplugin(plugin)

    with node.runtime():
        assert node.setup() is True
        requires = ",".join(node.task.get("require"))
        assert "var,passplugin" in requires
        assert "var,dialectplugin" in requires
        arguments = node.task.get_runtime_arguments()

    assert f"--load-pass-plugin={plugin}" in arguments
    assert f"--load-dialect-plugin={plugin}" in arguments
    assert arguments.index(f"--load-pass-plugin={plugin}") < \
        next(i for i, a in enumerate(arguments) if a.startswith("-pass-pipeline="))


def test_plugin_setters_are_independent(mm_design, datadir):
    """A dialect-only plugin does not get a pass flag it would only warn about."""
    node = _node(mm_design, BufferizeTask(), step="opt")

    plugin = os.path.join(datadir, "mm.mlir")
    BufferizeTask.find_task(node.project).add_mlir_dialectplugin(plugin)

    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    # Both pass forms share the parameters, so this works from either.
    assert arguments.index(f"--load-dialect-plugin={plugin}") < \
        arguments.index("--canonicalize")
    assert not [a for a in arguments if a.startswith("--load-pass-plugin")]


def test_no_plugin_options_when_unset(mm_design):
    """The flags appear only when a plugin is named."""
    node = _node(mm_design, TosaToLinalgTask(), step="opt")
    with node.runtime():
        assert node.setup() is True
        requires = ",".join(node.task.get("require"))
        arguments = node.task.get_runtime_arguments()

    assert not [a for a in arguments if a.startswith("--load-")]
    assert "var,passplugin" not in requires
    assert "var,dialectplugin" not in requires


def test_setters_per_node():
    task = PipelineTask()
    task.set_mlir_pipeline("builtin.module(cse)", step="opt", index="1")
    assert task.get("var", "pipeline", step="opt", index="1") == "builtin.module(cse)"
    assert not task.get("var", "pipeline")


def test_translate_runtime_opts(mm_design, datadir):
    node = _node(mm_design, TranslateTask(), step="translate")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert arguments == [
        "--mlir-to-llvmir",
        os.path.join(datadir, "mm.mlir"),
        "-o", os.path.join("outputs", "forward_kernel.ll"),
    ]


def test_translate_setters():
    task = TranslateTask()
    assert task.get("var", "stripintrinsics") == \
        ["llvm.stacksave.p0", "llvm.stackrestore.p0"]

    task.set_mlir_action("--mlir-to-cpp")
    assert task.get("var", "action") == "--mlir-to-cpp"

    task.add_mlir_stripintrinsics([], clobber=True)
    assert task.get("var", "stripintrinsics") == []

    task.add_mlir_stripintrinsics("llvm.donothing")
    assert task.get("var", "stripintrinsics") == ["llvm.donothing"]


def test_translate_strips_intrinsics(mm_design):
    """post_process drops the stack save/restore lines an HLS tool cannot read."""
    node = _node(mm_design, TranslateTask(), step="translate")

    outputs = pathlib.Path("outputs")
    outputs.mkdir()

    (outputs / "forward_kernel.ll").write_text(
        "define void @forward_kernel(ptr %0) {\n"
        "  %2 = call ptr @llvm.stacksave.p0()\n"
        "  call void @llvm.stackrestore.p0(ptr %2)\n"
        "  ret void\n"
        "}\n"
        "declare ptr @llvm.stacksave.p0()\n")

    with node.runtime():
        assert node.setup() is True
        node.task.post_process()

    remaining = (outputs / "forward_kernel.ll").read_text()
    assert "stacksave" not in remaining
    assert "stackrestore" not in remaining
    assert "define void @forward_kernel(ptr %0) {" in remaining
    assert "ret void" in remaining


def test_runtime_compile_runtime_opts(mm_design):
    node = _node(mm_design, RuntimeTask(), step="runtime")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert arguments[:5] == ["-S", "-emit-llvm", "-O0",
                             "-o", os.path.join("outputs", "memref_copy.ll")]
    assert arguments[-1].endswith(os.path.join("mlir", "data", "memref_copy.c"))
    assert os.path.isfile(arguments[-1])


def test_runtime_compile_declares_output(mm_design):
    node = _node(mm_design, RuntimeTask(), step="runtime")
    with node.runtime():
        assert node.setup() is True
        # Named after the source rather than the design, because it is not the
        # design: LinkTask picks it up as "the upstream module that is not the
        # kernel".
        assert node.task.get("output") == ["memref_copy.ll"]
        # No design input at all, so it can be an entry node.
        assert node.task.get("input") == []


def test_runtime_source_setter(mm_design, datadir):
    """The source is a parameter, and the module it produces is named after it."""
    task = RuntimeTask()
    assert task._get_runtime_ir() == "memref_copy.ll"

    node = _node(mm_design, task, step="runtime")

    source = os.path.join(datadir, "gcd.c")
    RuntimeTask.find_task(node.project).set_mlir_source(source)

    with node.runtime():
        assert node.setup() is True
        assert node.task._get_runtime_ir() == "gcd.ll"
        assert node.task.get("output") == ["gcd.ll"]
        arguments = node.task.get_runtime_arguments()

    assert arguments[3:5] == ["-o", os.path.join("outputs", "gcd.ll")]
    assert arguments[-1] == source


def test_runtime_source_required(mm_design):
    """Clearing the source leaves nothing to name the output after, so setup
    declares none and the run stops at the required-key check."""
    node = _node(mm_design, RuntimeTask(), step="runtime")
    task = RuntimeTask.find_task(node.project)
    task.set("var", "source", None)
    assert task._get_runtime_ir() is None

    with node.runtime():
        assert node.setup() is True
        assert node.task.get("output") == []
        assert "var,source" in ",".join(node.task.get("require"))
        assert node.validate() is False


def test_link_without_input(mm_design):
    """A link node with nothing upstream has nothing to link."""
    node = _node(mm_design, LinkTask(), step="link")
    with node.runtime():
        assert node.setup() is True
        with pytest.raises(ValueError, match="has no input"):
            node.task.runtime_options()


def _link_flow(design):
    """A link node fed by a runtime node and a translate node, as the flow wires it."""
    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("translate", TranslateTask())
    flow.node("runtime", RuntimeTask())
    flow.node("link", LinkTask())
    flow.edge("translate", "link")
    flow.edge("runtime", "link")
    proj.set_flow(flow)

    return proj


def test_link_declares_both_inputs(mm_design):
    proj = _link_flow(mm_design)
    _setup_upstream(proj, "translate", "runtime")

    node = SchedulerNode(proj, "link", "0")
    with node.runtime():
        assert node.setup() is True
        assert sorted(node.task.get("input")) == ["forward_kernel.ll", "memref_copy.ll"]


@pytest.mark.parametrize("module,linked", [
    # Calls the helper and does not define it: the definition has to be merged in.
    ("declare void @memrefCopy(i64, ptr, ptr)\n"
     "define void @forward_kernel(ptr %0) {\n"
     "  call void @memrefCopy(i64 4, ptr %0, ptr %0)\n"
     "  ret void\n}\n", True),
    # Never mentions it, so merging one in would only leave a dead function
    # for the HLS tool to carry.
    ("define void @forward_kernel(ptr %0) {\n  ret void\n}\n", False),
    # Already defines it; merging would be a duplicate symbol.
    ("define void @memrefCopy(i64 %0, ptr %1, ptr %2) {\n  ret void\n}\n"
     "define void @forward_kernel(ptr %0) {\n"
     "  call void @memrefCopy(i64 4, ptr %0, ptr %0)\n"
     "  ret void\n}\n", False),
])
def test_link_merges_runtime_only_when_needed(mm_design, module, linked):
    proj = _link_flow(mm_design)
    _setup_upstream(proj, "translate", "runtime")

    node = SchedulerNode(proj, "link", "0")

    inputs = pathlib.Path("inputs")
    inputs.mkdir()
    (inputs / "forward_kernel.ll").write_text(module)
    (inputs / "memref_copy.ll").write_text(
        "define void @memrefCopy(i64 %0, ptr %1, ptr %2) {\n  ret void\n}\n")

    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    runtime_ir = os.path.join("inputs", "memref_copy.ll")
    assert (runtime_ir in arguments) is linked
    assert arguments[0] == "-S"
    assert arguments[-3:] == [os.path.join("inputs", "forward_kernel.ll"),
                              "-o", os.path.join("outputs", "forward_kernel.ll")]


def test_link_runtimesupport_setter(mm_design):
    proj = _link_flow(mm_design)
    LinkTask.find_task(proj).set_mlir_runtimesupport(False)
    _setup_upstream(proj, "translate", "runtime")

    node = SchedulerNode(proj, "link", "0")

    inputs = pathlib.Path("inputs")
    inputs.mkdir()
    (inputs / "forward_kernel.ll").write_text(
        "declare void @memrefCopy(i64, ptr, ptr)\n")
    (inputs / "memref_copy.ll").write_text("")

    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert os.path.join("inputs", "memref_copy.ll") not in arguments


def test_upstream_input_is_not_faked_from_filesets(mm_design):
    """A node the flow feeds must never fall back to the design's own sources.

    Falling back would re-read the original TOSA and silently drop every
    transformation the upstream nodes made.
    """
    proj = Project(mm_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("tosa2linalg", TosaToLinalgTask())
    flow.node("bufferize", BufferizeTask())
    flow.edge("tosa2linalg", "bufferize")
    proj.set_flow(flow)
    _setup_upstream(proj, "tosa2linalg")

    node = SchedulerNode(proj, "bufferize", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert os.path.join("inputs", "forward_kernel.mlir") in arguments
    assert not any(arg.endswith("mm.mlir") for arg in arguments)


def test_tool_name():
    for task in (PipelineTask(), PassesTask(), TranslateTask(), LinkTask(), RuntimeTask()):
        assert isinstance(task, MLIRTask)
        assert task.tool() == "mlir"

    # Each task in the folder needs its own name, since a project registers a
    # task under (tool, task).
    names = [task.task() for task in (PipelineTask(), PassesTask(), TosaToLinalgTask(),
                                      BufferizeTask(), LinalgToLLVMTask(), TranslateTask(),
                                      LinkTask(), RuntimeTask())]
    assert len(names) == len(set(names))


def _post_process_records(node):
    """Runs a node's post_process() with its record_metric() calls captured.

    There is no lines metric in the schema, so record_metric drops the value and
    it cannot be read back out of the project; capturing the call is also what
    makes the path the count was recorded against visible.
    """
    recorded = []

    with node.runtime():
        assert node.setup() is True

        real = node.task.record_metric

        def capture(metric, value, source_file=None, **kwargs):
            recorded.append((metric, value, source_file))
            return real(metric, value, source_file, **kwargs)

        node.task.record_metric = capture
        node.task.post_process()

    return recorded


@pytest.mark.parametrize("content,lines", [
    ("one\ntwo\nthree\n", 3),
    # wc -l reports two here, having no newline to count for the last line. It
    # is still a line the downstream node reads, so it counts.
    ("one\ntwo\nthree", 3),
    ("", 0),
    ("\n", 1),
])
def test_record_output_lines(mm_design, content, lines):
    node = _node(mm_design, LinkTask(), step="link")

    outputs = pathlib.Path("outputs")
    outputs.mkdir()
    (outputs / "forward_kernel.ll").write_text(content)

    with node.runtime():
        assert node.setup() is True
        assert node.task._record_output_lines(
            os.path.join("outputs", "forward_kernel.ll")) == lines


def test_opt_post_process_records_lines(mm_design):
    """Both pass forms write the same file, so the count comes from the base."""
    node = _node(mm_design, BufferizeTask(), step="bufferize")

    outputs = pathlib.Path("outputs")
    outputs.mkdir()
    (outputs / "forward_kernel.mlir").write_text(
        "module {\n"
        "  func.func @forward_kernel() {\n"
        "    return\n"
        "  }\n"
        "}\n")

    assert _post_process_records(node) == \
        [("lines", 5, os.path.join("outputs", "forward_kernel.mlir"))]


def test_translate_post_process_records_lines_after_stripping(mm_design):
    """The count has to describe what the next node reads, so it is taken after
    the intrinsic lines are dropped rather than before."""
    node = _node(mm_design, TranslateTask(), step="translate")

    outputs = pathlib.Path("outputs")
    outputs.mkdir()
    (outputs / "forward_kernel.ll").write_text(
        "define void @forward_kernel(ptr %0) {\n"
        "  %2 = call ptr @llvm.stacksave.p0()\n"
        "  call void @llvm.stackrestore.p0(ptr %2)\n"
        "  ret void\n"
        "}\n"
        "declare ptr @llvm.stacksave.p0()\n")

    # Six lines in, three of them referencing the intrinsics.
    assert _post_process_records(node) == \
        [("lines", 3, os.path.join("outputs", "forward_kernel.ll"))]


def test_translate_post_process_records_lines_without_stripping(mm_design):
    """Nothing to strip is not nothing to count: the IR is handed on either way."""
    node = _node(mm_design, TranslateTask(), step="translate")
    TranslateTask.find_task(node.project).add_mlir_stripintrinsics([], clobber=True)

    outputs = pathlib.Path("outputs")
    outputs.mkdir()
    (outputs / "forward_kernel.ll").write_text(
        "define void @forward_kernel(ptr %0) {\n"
        "  %2 = call ptr @llvm.stacksave.p0()\n"
        "  ret void\n"
        "}\n")

    assert _post_process_records(node) == \
        [("lines", 4, os.path.join("outputs", "forward_kernel.ll"))]


def test_link_post_process_records_lines(mm_design):
    node = _node(mm_design, LinkTask(), step="link")

    outputs = pathlib.Path("outputs")
    outputs.mkdir()
    (outputs / "forward_kernel.ll").write_text(
        "define void @forward_kernel(ptr %0) {\n"
        "  ret void\n"
        "}\n")

    assert _post_process_records(node) == \
        [("lines", 3, os.path.join("outputs", "forward_kernel.ll"))]


def test_runtime_post_process_records_lines_after_stripping(mm_design):
    """Taken after the target lines come back out, which is the module
    llvm-link is handed."""
    node = _node(mm_design, RuntimeTask(), step="runtime")

    outputs = pathlib.Path("outputs")
    outputs.mkdir()
    (outputs / "memref_copy.ll").write_text(
        "target datalayout = \"e-m:e-p270:32:32\"\n"
        "target triple = \"x86_64-unknown-linux-gnu\"\n"
        "define void @memrefCopy(i64 %0, ptr %1, ptr %2) {\n"
        "  ret void\n"
        "}\n")

    assert _post_process_records(node) == \
        [("lines", 3, os.path.join("outputs", "memref_copy.ll"))]


def test_lines_recorded_quietly(mm_design, caplog):
    """There is no lines metric to land in yet, so recording must not warn."""
    node = _node(mm_design, LinkTask(), step="link")

    outputs = pathlib.Path("outputs")
    outputs.mkdir()
    (outputs / "forward_kernel.ll").write_text(
        "define void @forward_kernel(ptr %0) {\n  ret void\n}\n")

    with node.runtime():
        assert node.setup() is True
        node.task.logger.propagate = True
        node.task.post_process()

    # What is pinned is the silence: quiet exists so that a node recording a
    # metric the schema has no key for does not warn on every run. Whether the
    # value lands is up to the schema, so it is deliberately not asserted here
    # -- adding a lines metric should not break this test.
    assert "not a valid metric" not in caplog.text


@pytest.mark.parametrize("task,step", [
    (BufferizeTask, "bufferize"),
    (TranslateTask, "translate"),
    (LinkTask, "link"),
    (RuntimeTask, "runtime"),
])
def test_no_output_to_count_is_not_an_error(mm_design, task, step):
    """post_process() runs whether or not the tool succeeded, so the output a
    failed node never wrote must not turn the real error into a traceback."""
    node = _node(mm_design, task(), step=step)

    pathlib.Path("outputs").mkdir()

    with node.runtime():
        assert node.setup() is True
        node.task.post_process()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("task", (TosaToLinalgTask, TranslateTask, LinkTask, RuntimeTask))
def test_version(mm_design, task):
    node = _node(mm_design, task(), step="version")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_tosa_to_linalg(mm_design):
    """The TOSA module lowers to linalg on buffers, which is what soda-opt outlines from."""
    proj = Project(mm_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("tosa2linalg", TosaToLinalgTask())
    flow.node("bufferize", BufferizeTask())
    flow.edge("tosa2linalg", "bufferize")
    proj.set_flow(flow)

    assert proj.run()

    linalg = proj.find_result("mlir", step="bufferize")
    assert linalg is not None

    with open(linalg) as f:
        lowered = f.read()

    # linalg on memrefs, with the result turned into an out-parameter.
    assert "tosa." not in lowered
    assert "memref<" in lowered


def test_link_handles_a_renamed_support_module(mm_design, datadir):
    """LinkTask takes whatever the upstream produced, not a name it knows.

    The support module is named after RuntimeTask's source, so hardcoding
    memref_copy.ll here would break the moment that source is changed.
    """
    proj = _link_flow(mm_design)
    RuntimeTask.find_task(proj).set_mlir_source(os.path.join(datadir, "gcd.c"))
    _setup_upstream(proj, "translate", "runtime")

    node = SchedulerNode(proj, "link", "0")

    inputs = pathlib.Path("inputs")
    inputs.mkdir()
    (inputs / "forward_kernel.ll").write_text(
        "declare void @memrefCopy(i64, ptr, ptr)\n"
        "define void @forward_kernel(ptr %0) {\n"
        "  call void @memrefCopy(i64 4, ptr %0, ptr %0)\n"
        "  ret void\n}\n")
    (inputs / "gcd.ll").write_text(
        "define void @memrefCopy(i64 %0, ptr %1, ptr %2) {\n  ret void\n}\n")

    with node.runtime():
        assert node.setup() is True
        assert sorted(node.task.get("input")) == ["forward_kernel.ll", "gcd.ll"]
        arguments = node.task.get_runtime_arguments()

    assert os.path.join("inputs", "gcd.ll") in arguments
    assert os.path.join("inputs", "memref_copy.ll") not in arguments


def test_link_requiredsymbol_setter(mm_design):
    """An empty required symbol links the support unconditionally."""
    proj = _link_flow(mm_design)
    LinkTask.find_task(proj).set_mlir_requiredsymbol("")
    _setup_upstream(proj, "translate", "runtime")

    node = SchedulerNode(proj, "link", "0")

    inputs = pathlib.Path("inputs")
    inputs.mkdir()
    # A kernel that never mentions the symbol would normally be left alone.
    (inputs / "forward_kernel.ll").write_text(
        "define void @forward_kernel(ptr %0) {\n  ret void\n}\n")
    (inputs / "memref_copy.ll").write_text(
        "define void @memrefCopy(i64 %0, ptr %1, ptr %2) {\n  ret void\n}\n")

    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert os.path.join("inputs", "memref_copy.ll") in arguments


@pytest.fixture
def copy_kernel_design(datadir):
    """A kernel calling memrefCopy, so the link task has something to merge."""
    design = Design("copy_kernel")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("copy_kernel")
        design.add_file("memref_copy_kernel.ll")
    return design


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_runtime_compile(mm_design):
    """clang really does compile the vendored support module, and the target
    lines that would stop llvm-link merging it really do come back out."""
    proj = Project(mm_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("runtime", RuntimeTask())
    proj.set_flow(flow)

    assert proj.run()

    module = proj.find_result("ll", step="runtime", filename="memref_copy.ll")
    assert module is not None

    with open(module) as f:
        ir = f.read()

    assert "define" in ir and "@memrefCopy" in ir
    # MLIR-generated IR carries neither, and llvm-link refuses to merge two
    # modules that disagree about them.
    assert "target triple" not in ir
    assert "target datalayout" not in ir


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_link_merges_runtime(copy_kernel_design):
    """The unresolved memrefCopy call is resolved inside the module."""
    proj = Project(copy_kernel_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("runtime", RuntimeTask())
    flow.node("link", LinkTask())
    flow.edge("runtime", "link")
    proj.set_flow(flow)

    assert proj.run()

    linked = proj.find_result("ll", step="link")
    assert linked is not None

    with open(linked) as f:
        ir = f.read()

    assert "define" in ir and "@memrefCopy" in ir
    assert "@copy_kernel" in ir
