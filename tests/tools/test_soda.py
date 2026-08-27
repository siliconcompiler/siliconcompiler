import pathlib
import pytest
import re

import os.path

from siliconcompiler import Design, Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.flows.sodaflow import (
    SODABaselineElaborationFlow, SODAOptimizedElaborationFlow, SODATransformedElaborationFlow)

from siliconcompiler.tools.mlir import MLIRTask
from siliconcompiler.tools.soda import SODATask, render_pipeline_options
from siliconcompiler.tools.soda.opt import (
    BaselineTask, OptimizedTask, OutlineTask, TransformedTask)


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


def _project(design, task, step="soda"):
    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node(step, task)
    proj.set_flow(flow)

    return proj


def _arguments(proj, step="soda"):
    node = SchedulerNode(proj, step, "0")
    with node.runtime():
        assert node.setup() is True
        return node.task.get_runtime_arguments()


def test_tool_and_task_names():
    for task in (BaselineTask(), OptimizedTask(), TransformedTask()):
        assert isinstance(task, SODATask)
        assert task.tool() == "soda"
        # soda-opt resembles the mlir tools because both wrap an LLVM command
        # line, not because it is one of them: they report different tools and
        # are installed by different scripts, so nothing that keys off the type
        # should confuse the two.
        assert not isinstance(task, MLIRTask)

    names = [task.task() for task in (BaselineTask(), OptimizedTask(), TransformedTask())]
    assert names == ["baseline", "optimized", "transformed"]


def test_parse_version():
    assert BaselineTask().parse_version(
        "LLVM (http://llvm.org/):\n"
        "  LLVM version 19.1.5\n"
        "  Optimized build.\n") == "19.1.5"


def test_render_pipeline_options():
    # None drops the option, True emits the bare flag, anything else is a value.
    assert render_pipeline_options([
        ("dropped", None),
        ("flag", True),
        ("count", 3),
    ]) == "flag count=3"
    assert render_pipeline_options([("dropped", None)]) == ""


def test_baseline_runtime_opts(mm_design, datadir):
    arguments = _arguments(_project(mm_design, BaselineTask()))

    assert arguments == [
        "--convert-all-to-soda",
        "-soda-outline-bambu-code",
        "-soda-extract-arguments-to-c-testbench=using-bare-ptr",
        "-soda-generate-bambu-accelcode=no-aa",
        "-lower-all-to-llvm=use-bare-ptr-memref-call-conv",
        "--convert-func-to-llvm",
        os.path.join(datadir, "mm.mlir"),
        "-o", os.path.join("outputs", "forward_kernel.mlir"),
    ]


def test_optimized_runtime_opts(mm_design):
    arguments = _arguments(_project(mm_design, OptimizedTask()))

    # The optimization pipeline replaces the plain lowering; everything else
    # about the front end is the same.
    assert "-lower-all-to-llvm=use-bare-ptr-memref-call-conv" not in arguments
    pipeline = [arg for arg in arguments
                if arg.startswith("-soda-opt-pipeline-for-bambu=")]
    assert len(pipeline) == 1
    assert pipeline[0] == (
        "-soda-opt-pipeline-for-bambu=use-bare-ptr-memref-call-conv "
        "number-of-full-unrolls=1 max-alloc-size-in-bytes=4096 "
        "max-rank-of-allocated-memref=3")


def test_optimized_pipeline_setters(mm_design):
    proj = _project(mm_design, OptimizedTask())

    task = OptimizedTask.find_task(proj)
    task.set_soda_tilesize(2)
    task.add_soda_permutation([1, 2, 0])
    task.set_soda_fullunrolls(3)

    arguments = _arguments(proj)
    pipeline, = [arg for arg in arguments if arg.startswith("-soda-opt-pipeline-for-bambu=")]

    assert "affine-tile-size=2" in pipeline
    assert "permutation-map=1,2,0" in pipeline
    assert "number-of-full-unrolls=3" in pipeline


def test_optimized_disable_setters(mm_design):
    """Each pipeline stage is a "remove this optimization" switch upstream, so
    turning one off here has to emit the corresponding no-* option."""
    proj = _project(mm_design, OptimizedTask())

    task = OptimizedTask.find_task(proj)
    task.set_soda_buffertrick(False)
    task.set_soda_allocapromotion(False)
    task.set_soda_scalarreplacement(False)

    arguments = _arguments(proj)
    pipeline, = [arg for arg in arguments if arg.startswith("-soda-opt-pipeline-for-bambu=")]

    assert "no-buffer-trick" in pipeline
    assert "no-alloca-promotion" in pipeline
    assert "no-scalar-replacement" in pipeline
    # The promotion limits mean nothing with promotion off, so they are dropped
    # rather than passed alongside the switch that disables them.
    assert "max-alloc-size-in-bytes" not in pipeline
    assert "max-rank-of-allocated-memref" not in pipeline


def test_optimized_promotion_limits(mm_design):
    proj = _project(mm_design, OptimizedTask())

    task = OptimizedTask.find_task(proj)
    task.set_soda_maxallocsize(8192)
    task.set_soda_maxmemrefrank(4)

    pipeline, = [arg for arg in _arguments(proj)
                 if arg.startswith("-soda-opt-pipeline-for-bambu=")]

    assert "max-alloc-size-in-bytes=8192" in pipeline
    assert "max-rank-of-allocated-memref=4" in pipeline


def test_transformed_requires_schedule(mm_design):
    """The transform schedule is what this strategy is, so it is a required key
    and a run without one stops at validation."""
    proj = _project(mm_design, TransformedTask())

    node = SchedulerNode(proj, "soda", "0")
    with node.runtime():
        assert node.setup() is True
        assert "var,schedule" in ",".join(node.task.get("require"))
        assert node.validate() is False


def test_transformed_runtime_opts(mm_design, datadir):
    proj = _project(mm_design, TransformedTask())

    schedule = os.path.join(datadir, "mm.mlir")
    TransformedTask.find_task(proj).set_soda_schedule(schedule)

    arguments = _arguments(proj)

    assert f"--transform-preload-library=transform-library-paths={schedule}" in arguments
    assert "--transform-interpreter" in arguments
    assert "--soda-transform-erase-schedule" in arguments
    assert "--lower-all-to-llvm=use-bare-ptr-memref-call-conv" in arguments

    # The transform passes have to run after the kernel is extracted and before
    # it is lowered, or there is nothing for the schedule to rewrite.
    assert arguments.index("-soda-generate-bambu-accelcode=no-aa") < \
        arguments.index("--transform-interpreter")
    assert arguments.index("--transform-interpreter") < \
        arguments.index("--lower-all-to-llvm=use-bare-ptr-memref-call-conv")


def test_anchorfunc_setter(mm_design):
    proj = _project(mm_design, BaselineTask())
    BaselineTask.find_task(proj).set_soda_anchorfunc("forward")

    arguments = _arguments(proj)
    assert "--convert-all-to-soda=anchor-func=forward" in arguments
    assert "--convert-all-to-soda" not in arguments


def test_barepointer_setter(mm_design):
    proj = _project(mm_design, BaselineTask())
    task = BaselineTask.find_task(proj)

    # The pipelines take this as a bare flag, so "off" is the option's absence
    # rather than a value.
    assert task._bare_pointer_option() == ("use-bare-ptr-memref-call-conv", True)
    task.set_soda_barepointer(False)
    assert task._bare_pointer_option() == ("use-bare-ptr-memref-call-conv", None)

    arguments = _arguments(proj)
    assert "-lower-all-to-llvm" in arguments
    assert "-soda-extract-arguments-to-c-testbench=" in arguments


def test_noaliasanalysis_setter(mm_design):
    proj = _project(mm_design, BaselineTask())
    BaselineTask.find_task(proj).set_soda_noaliasanalysis(False)

    arguments = _arguments(proj)
    assert "-soda-generate-bambu-accelcode" in arguments
    assert "-soda-generate-bambu-accelcode=no-aa" not in arguments


def test_testbench_setters(mm_design):
    proj = _project(mm_design, BaselineTask())

    task = BaselineTask.find_task(proj)
    task.set_soda_testbench(False)
    task.set_soda_xmltestbench(True)

    node = SchedulerNode(proj, "soda", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        outputs = sorted(node.task.get("output"))

    assert "-soda-extract-arguments-to-c-testbench=using-bare-ptr" not in arguments
    assert "-soda-extract-arguments-to-xml=using-bare-ptr" in arguments

    # Only the files the enabled passes actually write are declared, because a
    # node errors on both a missing and an unexpected output.
    assert outputs == ["forward_kernel.mlir",
                       "forward_kernel_interface.xml",
                       "forward_kernel_test.xml"]


def test_default_outputs(mm_design):
    node = SchedulerNode(_project(mm_design, BaselineTask()), "soda", "0")
    with node.runtime():
        assert node.setup() is True
        assert sorted(node.task.get("output")) == ["forward_kernel.mlir",
                                                   "forward_kernel_testbench.c"]


def test_printirafterall_setter(mm_design):
    proj = _project(mm_design, BaselineTask())
    assert "-mlir-print-ir-after-all" not in _arguments(proj)

    BaselineTask.find_task(proj).set_soda_printirafterall(True)
    assert "-mlir-print-ir-after-all" in _arguments(proj)


def test_plugin_setters(mm_design, datadir):
    """Passes and dialects are separate entry points, so they are separate
    parameters -- a library providing both is named to each."""
    proj = _project(mm_design, BaselineTask())

    plugin = os.path.join(datadir, "mm.mlir")  # any existing file resolves
    task = BaselineTask.find_task(proj)
    task.add_soda_passplugin(plugin)
    task.add_soda_dialectplugin(plugin)

    arguments = _arguments(proj)
    assert f"--load-pass-plugin={plugin}" in arguments
    assert f"--load-dialect-plugin={plugin}" in arguments
    # The plugin has to be loaded before the passes it provides are named.
    assert arguments.index(f"--load-pass-plugin={plugin}") < \
        arguments.index("--convert-all-to-soda")


def test_plugin_setters_are_independent(mm_design, datadir):
    """A pass-only plugin does not get a dialect flag it would only warn about."""
    proj = _project(mm_design, BaselineTask())

    plugin = os.path.join(datadir, "mm.mlir")
    BaselineTask.find_task(proj).add_soda_passplugin(plugin)

    arguments = _arguments(proj)
    assert f"--load-pass-plugin={plugin}" in arguments
    assert not [a for a in arguments if a.startswith("--load-dialect-plugin")]


def test_setters_per_node():
    task = OptimizedTask()
    task.set_soda_fullunrolls(4, step="soda", index="1")
    assert task.get("var", "fullunrolls", step="soda", index="1") == 4
    assert task.get("var", "fullunrolls") == 1


def test_post_process_collects_testbench(mm_design):
    """soda-opt writes the testbench into the working directory, named after the
    kernel it outlined; post_process moves it into outputs/."""
    node = SchedulerNode(_project(mm_design, BaselineTask()), "soda", "0")

    pathlib.Path("outputs").mkdir()
    pathlib.Path("outputs/forward_kernel.mlir").write_text("module {\n}\n")
    pathlib.Path("forward_kernel_testbench.c").write_text("int main() { return 0; }\n")

    with node.runtime():
        assert node.setup() is True
        node.task.post_process()

    assert pathlib.Path("outputs/forward_kernel_testbench.c").is_file()


def test_post_process_warns_on_kernel_mismatch(mm_design, caplog):
    """A topmodule that is not the outlined kernel would point the HLS tool at a
    function that does not exist, so it has to be reported rather than ignored."""
    node = SchedulerNode(_project(mm_design, BaselineTask()), "soda", "0")

    pathlib.Path("outputs").mkdir()
    pathlib.Path("outputs/forward_kernel.mlir").write_text("module {\n}\n")
    pathlib.Path("main_kernel_testbench.c").write_text("int main() { return 0; }\n")

    with node.runtime():
        assert node.setup() is True
        node.task.logger.propagate = True
        node.task.post_process()

    assert "outlined a kernel named 'main_kernel'" in caplog.text
    assert pathlib.Path("outputs/forward_kernel_testbench.c").is_file()


def test_post_process_missing_testbench(mm_design):
    node = SchedulerNode(_project(mm_design, BaselineTask()), "soda", "0")

    pathlib.Path("outputs").mkdir()

    with node.runtime():
        assert node.setup() is True
        with pytest.raises(FileNotFoundError, match="did not emit"):
            node.task.post_process()


def test_outline_task_is_abstract():
    """The base carries the front end but not a lowering, so it cannot be a node
    on its own: how the kernel is lowered is what a strategy chooses."""
    task = OutlineTask()
    with pytest.raises(NotImplementedError):
        task.task()
    with pytest.raises(NotImplementedError, match="flow-specific task"):
        task._lowering_options()


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
    """The count is soda's own, not the mlir tasks' -- the two families share no
    base, so this helper exists in both."""
    node = SchedulerNode(_project(mm_design, BaselineTask()), "soda", "0")

    outputs = pathlib.Path("outputs")
    outputs.mkdir()
    (outputs / "forward_kernel.mlir").write_text(content)

    with node.runtime():
        assert node.setup() is True
        assert node.task._record_output_lines(
            os.path.join("outputs", "forward_kernel.mlir")) == lines


def test_post_process_records_lines(mm_design):
    """The outlined kernel is what the HLS tool synthesizes, so its size is the
    one worth reporting."""
    node = SchedulerNode(_project(mm_design, BaselineTask()), "soda", "0")

    pathlib.Path("outputs").mkdir()
    pathlib.Path("outputs/forward_kernel.mlir").write_text(
        "module {\n"
        "  llvm.func @forward_kernel(%arg0: !llvm.ptr) {\n"
        "    llvm.return\n"
        "  }\n"
        "}\n")
    pathlib.Path("forward_kernel_testbench.c").write_text("int main() { return 0; }\n")

    assert _post_process_records(node) == \
        [("lines", 5, os.path.join("outputs", "forward_kernel.mlir"))]


def test_lines_recorded_quietly(mm_design, caplog):
    """There is no lines metric to land in yet, so recording must not warn."""
    proj = _project(mm_design, BaselineTask())
    node = SchedulerNode(proj, "soda", "0")

    pathlib.Path("outputs").mkdir()
    pathlib.Path("outputs/forward_kernel.mlir").write_text("module {\n}\n")
    pathlib.Path("forward_kernel_testbench.c").write_text("int main() { return 0; }\n")

    with node.runtime():
        assert node.setup() is True
        node.task.logger.propagate = True
        node.task.post_process()

    # What is pinned is the silence: quiet exists so that a node recording a
    # metric the schema has no key for does not warn on every run. Whether the
    # value lands is up to the schema, so it is deliberately not asserted here
    # -- adding a lines metric should not break this test.
    assert "not a valid metric" not in caplog.text


def test_no_module_to_count_is_not_an_error(mm_design):
    """post_process() runs whether or not soda-opt succeeded. With the testbench
    passes off there is nothing else for it to look for, so the missing module is
    the only thing that could raise -- and it must not, because the real error is
    the one worth reading."""
    node = SchedulerNode(_project(mm_design, BaselineTask()), "soda", "0")
    BaselineTask.find_task(node.project).set_soda_testbench(False)

    pathlib.Path("outputs").mkdir()

    with node.runtime():
        assert node.setup() is True
        node.task.post_process()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(mm_design):
    node = SchedulerNode(_project(mm_design, BaselineTask(), step="version"), "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.fixture
def mm_soda_design(datadir):
    """The model plus a transform schedule, as the SODA flow consumes them."""
    design = Design("mm")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"):
        with design.active_fileset("soda"):
            design.set_topmodule("forward_kernel")
            design.add_file("mm.mlir")
        with design.active_fileset("transform"):
            design.add_file("transform.mlir")
    return design


@pytest.mark.eda
@pytest.mark.timeout(1200)
def test_flow_simulates_with_the_generated_testbench(mm_soda_design):
    """The whole point of soda-opt emitting a testbench: bambu can simulate.

    The testbench reaches the HLS node over the soda -> convert edge, so turning
    simulation on is all a caller does -- no fileset naming a file the flow
    already produced.
    """
    from siliconcompiler import ASIC
    from siliconcompiler.targets import freepdk45_demo
    from siliconcompiler.tools.bambu.convert import ConvertTask

    proj = ASIC(mm_soda_design)
    proj.add_fileset("soda")
    freepdk45_demo(proj)
    proj.set_flow(SODABaselineElaborationFlow())

    ConvertTask.find_task(proj).set_bambu_simulate(True)

    assert proj.run()

    convert_dir = os.path.join("build", "mm", "job0", "convert", "0")
    # Staged from the soda node rather than resolved from a fileset.
    assert os.path.isfile(
        os.path.join(convert_dir, "inputs", "forward_kernel_testbench.c"))

    with open(os.path.join(convert_dir, "convert.log")) as f:
        log = f.read()

    assert "--generate-tb=inputs/forward_kernel_testbench.c" in log
    assert re.search(r"Total cycles\s*:\s*\d+", log)


@pytest.mark.eda
@pytest.mark.timeout(900)
@pytest.mark.parametrize("flowcls", (SODABaselineElaborationFlow,
                                     SODAOptimizedElaborationFlow,
                                     SODATransformedElaborationFlow))
def test_front_end(mm_soda_design, flowcls):
    """The whole SODA front end: TOSA in, LLVM IR for the outlined kernel out.

    Stops at the link step rather than running the HLS one, because that needs a
    bambu whose front-end compiler can read opaque pointers -- see the install
    note in the SODA tutorial. Everything ahead of it is what this covers: the
    TOSA lowering, the bufferization, the outlining and whichever lowering the
    flow under test chose.
    """
    from siliconcompiler import ASIC
    from siliconcompiler.targets import freepdk45_demo

    proj = ASIC(mm_soda_design)
    proj.add_fileset("soda")
    freepdk45_demo(proj)

    proj.set_flow(flowcls())
    proj.option.set("to", ["link"])

    if flowcls is SODATransformedElaborationFlow:
        TransformedTask.find_task(proj).set_soda_schedule(
            mm_soda_design.find_files("fileset", "transform", "file", "mlir")[0])

    assert proj.run()

    # Linalg on buffers, with the result turned into an out-parameter, is the
    # form soda-opt outlines a kernel from.
    with open(proj.find_result("mlir", step="bufferize")) as f:
        bufferized = f.read()
    assert "tosa." not in bufferized
    assert "memref<" in bufferized

    # The kernel is named after the function it came from, which is what makes
    # the design's topmodule forward_kernel.
    with open(proj.find_result("mlir", step="soda")) as f:
        outlined = f.read()
    assert "@forward_kernel" in outlined

    assert proj.find_result("c", step="soda", filename="forward_kernel_testbench.c")

    with open(proj.find_result("ll", step="link")) as f:
        assert "define void @forward_kernel" in f.read()
