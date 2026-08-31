import json
import os
import pytest
import re
import shutil

import os.path

from siliconcompiler import ASIC, Project, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.bambu import convert


def _setup_upstream(proj, *steps):
    """Sets up the named nodes, as the scheduler does before running any of them.

    A node's outputs are declared by its own setup(), so a downstream node only
    sees what an upstream will hand it once that upstream has been set up.
    """
    for step in steps:
        node = SchedulerNode(proj, step, "0")
        with node.runtime():
            assert node.setup() is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_bambu(datadir):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    assert proj.run()

    # check that compilation succeeded
    assert proj.find_result('v', step='convert') == \
        os.path.abspath("build/gcd/job0/convert/0/outputs/gcd.v")


def test_runtime_args(gcd_design, datadir):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            os.path.abspath(os.path.join(datadir, 'gcd.c')),
            '-v3',
            '-lm',
            '--soft-float',
            '--memory-allocation-policy=NO_BRAM',
            '--channels-number=1',
            '--disable-function-proxy',
            '--top-fname=gcd'
        ]


def test_runtime_args_clock(gcd_design):
    """--clock-name is the clock port of the generated RTL, so it has to come from the
    port the SDC creates its clock on and not from the name of that clock. gcd.sdc says
    "create_clock -name core_clock ... [get_ports clk]"; naming the port core_clock
    would leave the SDC constraining a port that does not exist."""
    proj = Project(gcd_design)
    proj.add_fileset(["rtl", "sdc"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert '--clock-name=clk' in arguments
    assert '--clock-period=2.0' in arguments


def test_clock_period_uses_the_library_multiplier(gcd_design):
    """A library whose timing is not in ns scales the period bambu is given.

    The multiplier lives at ['tool','bambu','clock_multiplier'] on the main
    library, the same shape as the device name. Reading it from anywhere else
    fails silently -- valid() just returns False and the period stays unscaled,
    which is a 1000x error on a library like asap7 that works in ps.
    """
    from siliconcompiler import ASIC
    from siliconcompiler.tools.bambu import BambuStdCellLibrary

    mainlib = BambuStdCellLibrary()
    mainlib.set_name("testlib")
    mainlib.set_bambu_clock_multiplier(0.001)

    proj = ASIC(gcd_design)
    proj.add_fileset(["rtl", "sdc"])
    proj.set_mainlib(mainlib)

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    # gcd.sdc's period is 2.0; at 0.001 the library is working in ps.
    assert '--clock-period=0.002' in arguments


def test_libm_is_always_paired_with_soft_float(gcd_design, datadir):
    """--soft-float lowers FP into calls that land in libm, so bambu needs -lm
    to resolve them. The reference passes the pair on every invocation, so the
    driver does too rather than making every caller remember it."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert arguments.index('-lm') < arguments.index('--soft-float')


def test_printdot_setter(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset(["rtl", "sdc"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        assert '--print-dot' not in node.task.get_runtime_arguments()

    task.set_bambu_printdot(True)
    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        assert '--print-dot' in node.task.get_runtime_arguments()


def _simulating_project(datadir, **kwargs):
    """A project whose convert node simulates against a C testbench."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"):
        with design.active_fileset("rtl"):
            design.set_topmodule("gcd")
            design.add_file("gcd.c")
        with design.active_fileset("testbench"):
            design.add_file("gcd_tb.c")

    proj = ASIC(design)
    proj.add_fileset(["rtl", "testbench"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)
    task.set_bambu_simulate(True)
    task.add_bambu_testbenchfileset("gcd", "testbench")
    return proj, task


def test_verilator_parallel_defaults_to_the_bare_flag(datadir):
    """The reference pairs --verilator-parallel with --simulator=VERILATOR and
    passes no thread count, letting verilator choose."""
    proj, _ = _simulating_project(datadir)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert '--verilator-parallel' in arguments
    assert not [a for a in arguments if a.startswith('--verilator-parallel=')]


def test_verilator_parallel_setter(datadir):
    proj, task = _simulating_project(datadir)
    task.set_bambu_verilatorparallel(4)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert '--verilator-parallel=4' in arguments


def test_verilator_parallel_only_for_verilator(datadir):
    """bambu takes the flag only for verilator, so another simulator must not
    get it."""
    proj, task = _simulating_project(datadir)
    task.set_bambu_simulator("modelsim")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert '--simulator=MODELSIM' in arguments
    assert not [a for a in arguments if a.startswith('--verilator-parallel')]


def test_upstream_testbench_reaches_generate_tb(datadir):
    """A front end that emits the testbench alongside the IR needs no fileset.

    soda-opt writes <kernel>_testbench.c, so when the flow supplies it the node
    takes it from inputs/ rather than making the caller name a fileset that
    holds a file the flow already produced.
    """
    from siliconcompiler import ASIC
    from siliconcompiler.tools.builtin.importfiles import ImportFilesTask

    scroot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    kernel = os.path.join(scroot, "examples", "mlir_hls", "main_kernel.ll")

    design = Design("main_kernel")
    design.set_dataroot("root", os.path.dirname(kernel))
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("main_kernel")
        design.add_file("main_kernel.ll")

    proj = ASIC(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("stage", ImportFilesTask())
    flow.node("convert", convert.ConvertTask())
    flow.edge("stage", "convert")
    proj.set_flow(flow)

    # Stand in for the soda node: hand over both the IR and the testbench.
    stage = ImportFilesTask.find_task(proj)
    stage.add_import_file(kernel)
    stage.add_import_file(os.path.join(datadir, "main_kernel_testbench.c"))

    convert.ConvertTask.find_task(proj).set_bambu_simulate(True)

    _setup_upstream(proj, "stage")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        # Taken from the flow, so it is a declared input rather than a fileset.
        assert "main_kernel_testbench.c" in node.task.get("input")
        assert "var,testbench_fileset" not in ",".join(node.task.get("require"))
        arguments = node.task.get_runtime_arguments()

    assert f'--generate-tb={os.path.join("inputs", "main_kernel_testbench.c")}' in arguments


def test_upstream_xml_testbench_is_accepted(datadir):
    """--generate-tb takes a testbench XML as readily as a C file, and that is
    what soda-opt emits when asked for test vectors instead."""
    from siliconcompiler import ASIC
    from siliconcompiler.tools.builtin.importfiles import ImportFilesTask

    scroot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    kernel = os.path.join(scroot, "examples", "mlir_hls", "main_kernel.ll")

    design = Design("main_kernel")
    design.set_dataroot("root", os.path.dirname(kernel))
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("main_kernel")
        design.add_file("main_kernel.ll")

    proj = ASIC(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("stage", ImportFilesTask())
    flow.node("convert", convert.ConvertTask())
    flow.edge("stage", "convert")
    proj.set_flow(flow)

    stage = ImportFilesTask.find_task(proj)
    stage.add_import_file(kernel)
    # Test vectors, and the interface description that is not a testbench.
    stage.add_import_file(os.path.join(datadir, "main_kernel_test.xml"))
    stage.add_import_file(os.path.join(datadir, "main_kernel_interface.xml"))

    convert.ConvertTask.find_task(proj).set_bambu_simulate(True)

    _setup_upstream(proj, "stage")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        assert "main_kernel_test.xml" in node.task.get("input")
        arguments = node.task.get_runtime_arguments()

    assert f'--generate-tb={os.path.join("inputs", "main_kernel_test.xml")}' in arguments
    # bambu has no option that reads the interface description.
    assert not any("interface.xml" in a for a in arguments)


def test_c_testbench_wins_over_the_xml_one(datadir):
    """Both forms can be produced at once; the C one is what the reference
    flow simulates against."""
    from siliconcompiler import ASIC
    from siliconcompiler.tools.builtin.importfiles import ImportFilesTask

    scroot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    kernel = os.path.join(scroot, "examples", "mlir_hls", "main_kernel.ll")

    design = Design("main_kernel")
    design.set_dataroot("root", os.path.dirname(kernel))
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("main_kernel")
        design.add_file("main_kernel.ll")

    proj = ASIC(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("stage", ImportFilesTask())
    flow.node("convert", convert.ConvertTask())
    flow.edge("stage", "convert")
    proj.set_flow(flow)

    stage = ImportFilesTask.find_task(proj)
    stage.add_import_file(kernel)
    stage.add_import_file(os.path.join(datadir, "main_kernel_testbench.c"))
    stage.add_import_file(os.path.join(datadir, "main_kernel_test.xml"))

    convert.ConvertTask.find_task(proj).set_bambu_simulate(True)

    _setup_upstream(proj, "stage")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert f'--generate-tb={os.path.join("inputs", "main_kernel_testbench.c")}' in arguments
    assert not any("test.xml" in a for a in arguments)


def test_named_fileset_wins_over_the_upstream_testbench(datadir):
    """An explicitly named fileset is a choice, so it beats the flow's default."""
    from siliconcompiler import ASIC
    from siliconcompiler.tools.builtin.importfiles import ImportFilesTask

    scroot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    kernel = os.path.join(scroot, "examples", "mlir_hls", "main_kernel.ll")

    design = Design("main_kernel")
    design.set_dataroot("root", os.path.dirname(kernel))
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("main_kernel")
        design.add_file("main_kernel.ll")
    design.set_dataroot("tb", datadir)
    with design.active_dataroot("tb"), design.active_fileset("testbench"):
        design.add_file("gcd_tb.c")

    proj = ASIC(design)
    proj.add_fileset(["rtl", "testbench"])

    flow = Flowgraph("testflow")
    flow.node("stage", ImportFilesTask())
    flow.node("convert", convert.ConvertTask())
    flow.edge("stage", "convert")
    proj.set_flow(flow)

    stage = ImportFilesTask.find_task(proj)
    stage.add_import_file(kernel)
    stage.add_import_file(os.path.join(datadir, "main_kernel_testbench.c"))

    task = convert.ConvertTask.find_task(proj)
    task.set_bambu_simulate(True)
    task.add_bambu_testbenchfileset("main_kernel", "testbench")

    _setup_upstream(proj, "stage")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert any(a.endswith("gcd_tb.c") for a in arguments if a.startswith("--generate-tb="))
    assert not any("main_kernel_testbench.c" in a for a in arguments)


def test_technology_file_without_constraints_is_rejected(datadir):
    """bambu takes both XMLs positionally, so a technology file on its own would
    be read as the constraints file. There is no way to skip the first slot, so
    the configuration is refused instead of silently mis-parsed."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)
    task.set_bambu_technologyfile(os.path.join(datadir, "main_kernel_interface.xml"))

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        with pytest.raises(ValueError, match="technology file needs a constraints file"):
            node.setup()

    # The other direction is fine: constraints alone occupies the slot it is
    # read from.
    task.set_bambu_constraintsfile(os.path.join(datadir, "main_kernel_test.xml"))
    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True


def test_ip_integration_options(gcd_design, datadir):
    """The IP integration inputs bambu takes, as parameters rather than raw
    options -- they are files, and a file that reaches a tool as a bare string
    is neither hashed into the cache key nor copied for a remote run.
    """
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)
    technology = os.path.join(datadir, "main_kernel_interface.xml")
    constraints = os.path.join(datadir, "main_kernel_test.xml")
    task.set_bambu_technologyfile(technology)
    task.set_bambu_constraintsfile(constraints)
    task.add_bambu_cnoparse(os.path.join(datadir, "gcd_tb.c"))
    task.add_bambu_fileinputdata(os.path.join(datadir, "gcd.c"))
    task.set_bambu_componentslibrary(True)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        requires = ",".join(node.task.get("require"))
        arguments = node.task.get_runtime_arguments()

    # bambu's usage is "<source_file> [<constraints_file>] [<technology_file>]".
    source = next(i for i, a in enumerate(arguments) if a.endswith("gcd.c"))
    assert arguments.index(constraints) > source
    assert arguments.index(technology) > arguments.index(constraints)

    assert f'--C-no-parse={os.path.join(datadir, "gcd_tb.c")}' in arguments
    assert f'--file-input-data={os.path.join(datadir, "gcd.c")}' in arguments
    assert '--generate-components-library' in arguments

    # Declared, so they are hashed and copied rather than being opaque strings.
    for var in ("constraintsfile", "technologyfile", "cnoparse", "fileinputdata"):
        assert f"var,{var}" in requires


def test_ip_integration_lists_are_comma_joined(gcd_design, datadir):
    """bambu parses both of these as one comma-separated list, not as repeats."""
    proj = Project(gcd_design)
    proj.add_fileset(["rtl", "sdc"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)
    task.add_bambu_fileinputdata([os.path.join(datadir, "gcd.c"),
                                  os.path.join(datadir, "gcd_tb.c")])

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    joined = [a for a in arguments if a.startswith("--file-input-data=")]
    assert len(joined) == 1
    assert joined[0] == "--file-input-data={},{}".format(
        os.path.join(datadir, "gcd.c"), os.path.join(datadir, "gcd_tb.c"))


def test_no_ip_options_by_default(gcd_design):
    """None of it reaches the command line unless it was asked for."""
    proj = Project(gcd_design)
    proj.add_fileset(["rtl", "sdc"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert not [a for a in arguments if a.startswith("--C-no-parse")]
    assert not [a for a in arguments if a.startswith("--file-input-data")]
    assert '--generate-components-library' not in arguments


def test_parameter_memorychannels():
    task = convert.ConvertTask()
    task.set_bambu_memorychannels(2)
    assert task.get("var", "memorychannels") == 2
    task.set_bambu_memorychannels(4, step='convert', index='1')
    assert task.get("var", "memorychannels", step='convert', index='1') == 4
    assert task.get("var", "memorychannels") == 2


def test_sdc_required(gcd_design):
    # Regression guard (P1): sdc files consumed by get_clock() in runtime_options
    # must be declared required so they are hashed (cache) and copied (remote runs).
    proj = Project(gcd_design)
    proj.add_fileset(["rtl", "sdc"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        requires = node.task.get("require")

    assert any(r.endswith("file,sdc") for r in requires), requires


def test_verbosity_is_on_the_command_line(gcd_design, datadir):
    """The resource summary post_process() reads is only printed at -v3."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = ASIC(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        assert "-v3" in node.task.get_runtime_arguments()


def _post_process_log(proj, log, datadir):
    """Runs post_process() over a captured bambu log, in an isolated node dir."""
    node = SchedulerNode(proj, "convert", "0")

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    # post_process copies the generated Verilog before it reads the log.
    with open("main_kernel.v", "w") as f:
        f.write("module main_kernel(); endmodule\n")

    with node.runtime():
        assert node.setup() is True
        shutil.copyfile(os.path.join(datadir, "bambu", log), node.task.get_logpath("exe"))
        node.task.post_process()

    return node


@pytest.fixture
def main_kernel_project(datadir):
    """An ASIC project for the kernel the captured logs were produced from."""
    from siliconcompiler import ASIC

    design = Design("main_kernel")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("main_kernel")
        design.add_file("gcd.c")

    proj = ASIC(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)
    return proj


def test_resource_summary_report(main_kernel_project, datadir):
    """The per-functional-unit tally becomes a cell usage report."""
    _post_process_log(main_kernel_project, "simulated_run.txt", datadir)

    with open(os.path.join("reports", "resource_usage.json")) as f:
        report = json.load(f)

    # Counts as bambu printed them, including a unit whose name is not an FU.
    assert report["MUX_GATE"]["cellcount"] == 52
    assert report["register_STD"]["cellcount"] == 33
    assert report["flipflop_AR"]["cellcount"] == 2
    assert report["truth_and_expr_FU"]["cellcount"] == 81
    assert report["constant_value"]["cellcount"] == 58

    # Every entry in the block, and nothing from the lines that follow it --
    # the captured log goes on to compile and simulate.
    assert len(report) == 35
    assert all(entry["cellarea"] is None for entry in report.values())


def test_printdot_graphs_are_collected_as_reports(main_kernel_project, datadir):
    """--print-dot writes a design-shaped tree of graphs, so they are reports.

    They cannot be outputs: outputs/ is checked against the declared list and an
    undeclared file there fails the node, while the number and names of these
    depend on the functions in the design.
    """
    task = convert.ConvertTask.find_task(main_kernel_project)
    task.set_bambu_printdot(True)

    dot_dir = os.path.join("HLS_output", "dot", "main_kernel")
    os.makedirs(dot_dir, exist_ok=True)
    with open(os.path.join(dot_dir, "OP_CFG.dot"), "w") as f:
        f.write("digraph {}\n")
    with open(os.path.join("HLS_output", "dot", "call_graph.dot"), "w") as f:
        f.write("digraph {}\n")

    _post_process_log(main_kernel_project, "simulated_run.txt", datadir)

    # The tree is preserved, including the per-function subdirectory.
    assert os.path.isfile(os.path.join("reports", "dot", "call_graph.dot"))
    assert os.path.isfile(os.path.join("reports", "dot", "main_kernel", "OP_CFG.dot"))
    # And nothing leaked into outputs/, which would fail the node.
    assert not os.path.exists(os.path.join("outputs", "dot"))


def test_no_dot_reports_when_printdot_is_off(main_kernel_project, datadir):
    """The default run does not produce them, so nothing is collected."""
    _post_process_log(main_kernel_project, "simulated_run.txt", datadir)

    assert not os.path.exists(os.path.join("reports", "dot"))


def test_cycles_recorded_quietly(main_kernel_project, datadir, caplog):
    """Cycles have no metric to land in yet, so recording must not warn."""
    _post_process_log(main_kernel_project, "simulated_run.txt", datadir)

    # The log reports 1286 cycles, and there is nowhere to put them yet. What
    # matters is that this is silent rather than a warning on every run.
    assert "cycles" not in main_kernel_project.getkeys("metric")
    assert "not a valid metric" not in caplog.text

    # The metrics that do exist still come out of the same pass over the log.
    assert main_kernel_project.get("metric", "registers",
                                   step="convert", index="0") == 1951


def test_no_resource_report_without_the_block(main_kernel_project, datadir, tmp_path):
    """A log with no resource summary leaves no report behind."""
    log = tmp_path / "quiet.log"
    log.write_text("Total number of flip-flops in function main_kernel: 12\n")

    node = SchedulerNode(main_kernel_project, "convert", "0")
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    with open("main_kernel.v", "w") as f:
        f.write("module main_kernel(); endmodule\n")

    with node.runtime():
        assert node.setup() is True
        shutil.copyfile(log, node.task.get_logpath("exe"))
        node.task.post_process()

    assert not os.path.exists(os.path.join("reports", "resource_usage.json"))


def test_cycles_are_parsed_even_though_nothing_stores_them(main_kernel_project, datadir):
    """The value is read now, so it lands the day a cycles metric exists.

    record_metric() drops an unknown metric on the floor, so the parse cannot be
    observed through the schema; capture the call instead. Without this the
    regex could rot silently until someone adds the metric and wonders why it
    is empty.
    """
    node = SchedulerNode(main_kernel_project, "convert", "0")

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    with open("main_kernel.v", "w") as f:
        f.write("module main_kernel(); endmodule\n")

    recorded = []

    with node.runtime():
        assert node.setup() is True
        shutil.copyfile(os.path.join(datadir, "bambu", "simulated_run.txt"),
                        node.task.get_logpath("exe"))

        real = node.task.record_metric

        def capture(metric, value, *args, **kwargs):
            recorded.append((metric, value))
            return real(metric, value, *args, **kwargs)

        node.task.record_metric = capture
        node.task.post_process()

    # "Total cycles             : 1286 cycles" in the captured log.
    assert ("cycles", 1286) in recorded


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_resource_report_from_a_real_run(datadir):
    """bambu really is run at -v3, and the summary really is parseable."""
    from siliconcompiler.targets import freepdk45_demo

    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    assert proj.run()

    report = os.path.join("build", "gcd", "job0", "convert", "0",
                          "reports", "resource_usage.json")
    assert os.path.isfile(report)

    with open(report) as f:
        resources = json.load(f)

    assert resources
    assert all(isinstance(entry["cellcount"], int) for entry in resources.values())
    # These are functional units the scheduler allocated; nothing has mapped
    # them onto a technology, so no area is claimed for them.
    assert all(entry["cellarea"] is None for entry in resources.values())


def test_simulation_is_off_by_default(gcd_design, datadir):
    """Simulation is slow and needs a testbench, so nothing is added unasked."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = ASIC(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert "--simulate" not in arguments
    assert not any(arg.startswith(("--simulator", "--generate-tb")) for arg in arguments)


def test_simulation_options(gcd_design, datadir):
    """The cycle counts only exist when bambu simulates, which needs all three."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"):
        with design.active_fileset("rtl"):
            design.set_topmodule("gcd")
            design.add_file("gcd.c")
        with design.active_fileset("testbench"):
            design.add_file("gcd_tb.c")

    proj = ASIC(design)
    proj.add_fileset(["rtl", "testbench"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)
    task.set_bambu_simulate(True)
    task.add_bambu_testbenchfileset("gcd", "testbench")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert "--simulate" in arguments
    assert "--simulator=VERILATOR" in arguments
    assert f"--generate-tb={os.path.join(datadir, 'gcd_tb.c')}" in arguments

    # The testbench is not part of the design, so it is not also compiled in.
    assert os.path.join(datadir, "gcd.c") in arguments
    assert len([a for a in arguments if a.endswith("gcd_tb.c")]) == 1
    assert not any(a == os.path.join(datadir, "gcd_tb.c") for a in arguments)


def test_simulation_without_a_testbench_is_rejected(gcd_design, datadir):
    """bambu cannot simulate without one, so the fileset is a required key
    whenever simulation is on and the run stops at validation."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = ASIC(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    convert.ConvertTask.find_task(proj).set_bambu_simulate(True)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        assert "var,testbench_fileset" in ",".join(node.task.get("require"))
        assert node.validate() is False


def test_simulator_setter(gcd_design, datadir):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"):
        with design.active_fileset("rtl"):
            design.set_topmodule("gcd")
            design.add_file("gcd.c")
        with design.active_fileset("testbench"):
            design.add_file("gcd_tb.c")

    proj = ASIC(design)
    proj.add_fileset(["rtl", "testbench"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)
    task.set_bambu_simulate(True)
    task.set_bambu_simulator("modelsim")
    task.add_bambu_testbenchfileset("gcd", "testbench")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        # Held lower case, spelled the way bambu wants on the way out.
        assert "--simulator=MODELSIM" in node.task.get_runtime_arguments()


def test_simulator_is_an_enum():
    """bambu accepts exactly three, and rejects anything else itself."""
    task = convert.ConvertTask()
    assert task.get("var", "simulator") == "verilator"

    for simulator in ("modelsim", "xsim", "verilator"):
        task.set_bambu_simulator(simulator)
        assert task.get("var", "simulator") == simulator

    # Including the upper case bambu itself uses, so there is one spelling.
    for rejected in ("VERILATOR", "icarus"):
        with pytest.raises(ValueError):
            task.set_bambu_simulator(rejected)


@pytest.mark.eda
@pytest.mark.timeout(900)
def test_simulation_reports_cycles(datadir):
    """Simulating really does produce the cycle counts the driver parses.

    Needs a working simulation toolchain -- verilator plus the headers bambu's
    MDPI runtime compiles against (linux-libc-dev and the 32-bit sets); without
    them bambu fails building its wrapper rather than reporting anything.
    """
    from siliconcompiler.targets import freepdk45_demo

    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"):
        with design.active_fileset("rtl"):
            design.set_topmodule("gcd")
            design.add_file("gcd.c")
        with design.active_fileset("testbench"):
            design.add_file("gcd_tb.c")

    proj = ASIC(design)
    proj.add_fileset(["rtl", "testbench"])
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)
    task.set_bambu_simulate(True)
    task.add_bambu_testbenchfileset("gcd", "testbench")

    assert proj.run()

    with open(os.path.join("build", "gcd", "job0", "convert", "0", "convert.log")) as f:
        log = f.read()

    # The parser reads this line; without simulation it is never printed.
    assert re.search(r"Total cycles\s*:\s*\d+", log)
    # And the design still built.
    assert proj.find_result("v", step="convert") is not None


def test_asic_without_a_target(gcd_design):
    """An ASIC project that has not loaded a target still builds a command line.

    ['asic','mainlib'] is a valid keypath on every ASIC project but is empty
    until a target fills it in, so asking whether the keypath is valid says
    nothing about whether there is a library to read a device name from. The
    clock multiplier is read the same way and has the same trap.
    """
    proj = ASIC(gcd_design)
    proj.add_fileset(["rtl", "sdc"])

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    # No target, so no device to estimate against and no clock multiplier.
    assert not any(arg.startswith("--device") for arg in arguments)
    assert "--clock-period=2.0" in arguments


def test_parameter_bambu_options(gcd_design, datadir):
    """The knobs the SODA flow needs from bambu, and that they stay off the
    command line until they are set."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    task = convert.ConvertTask.find_task(proj)
    assert task.get("var", "memorypolicy") == "NO_BRAM"
    assert not task.get("var", "experimentalsetup")
    assert not task.get("var", "compiler")

    task.set_bambu_memorypolicy("ALL_BRAM")
    task.set_bambu_experimentalsetup("BAMBU-BALANCED-MP")
    task.set_bambu_compiler("I386_CLANG16")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert "--memory-allocation-policy=ALL_BRAM" in arguments
    assert "--experimental-setup=BAMBU-BALANCED-MP" in arguments
    assert "--compiler=I386_CLANG16" in arguments


def test_llvm_from_upstream_node(gcd_design, datadir):
    """An MLIR front end hands bambu the LLVM IR to synthesize, so a staged .ll
    input has to win over whatever the design's filesets hold -- and the include
    paths, defines and sources in them describe a compilation bambu is no longer
    doing, so none of them reach the command line or the required keys."""
    from siliconcompiler.tools.mlir.link import LinkTask

    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")
        design.add_idir(".")
        design.add_define("WIDTH=8")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("link", LinkTask())
    flow.node("convert", convert.ConvertTask())
    flow.edge("link", "convert")
    proj.set_flow(flow)

    link = SchedulerNode(proj, "link", "0")
    with link.runtime():
        assert link.setup() is True

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get("input") == ["gcd.ll"]
        requires = node.task.get("require")

        os.makedirs("inputs", exist_ok=True)
        with open(os.path.join("inputs", "gcd.ll"), "w") as f:
            f.write("define void @gcd() {\n  ret void\n}\n")

        arguments = node.task.get_runtime_arguments()

    assert os.path.join("inputs", "gcd.ll") in arguments
    assert not any(arg.endswith("gcd.c") for arg in arguments)
    assert not any(arg.startswith(("-I", "-D")) for arg in arguments)

    # Nothing the C front end would have used is declared an input of this node,
    # so its cache key does not depend on files it never opens.
    for unused in ("file,c", "file,llvm", "idir", "define"):
        assert not any(r.endswith(unused) for r in requires), (unused, requires)


def test_c_sources_still_carry_their_compile_flags(datadir):
    """The fileset path is unchanged: bambu is the compiler there, so it needs
    the include paths, the defines and the sources."""
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")
        design.add_idir(".")
        design.add_define("WIDTH=8")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        requires = node.task.get("require")

    assert any(arg.startswith("-I") for arg in arguments)
    assert "-DWIDTH=8" in arguments
    assert any(arg.endswith("gcd.c") for arg in arguments)
    assert any(r.endswith("file,c") for r in requires)
    assert any(r.endswith("idir") for r in requires)
    assert any(r.endswith("define") for r in requires)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_llvm_from_upstream_node_run(datadir):
    """bambu synthesizes LLVM IR handed to it by an upstream node.

    This is how the MLIR front ends reach bambu: the design's filesets hold
    MLIR, and the IR to synthesize is produced by the flow. The import task
    stages the IR verbatim, standing in for that front end.
    """
    from siliconcompiler import ASIC
    from siliconcompiler.targets import freepdk45_demo
    from siliconcompiler.tools.builtin.importfiles import ImportFilesTask

    scroot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    kernel = os.path.join(scroot, "examples", "mlir_hls", "main_kernel.ll")

    design = Design("main_kernel")
    design.set_dataroot("root", os.path.dirname(kernel))
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("main_kernel")
        design.add_file("main_kernel.ll")

    # An ASIC project and a target: bambu's estimates are ASIC metrics, and the
    # device it estimates against comes from the target's main library.
    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node("stage", ImportFilesTask())
    flow.node("convert", convert.ConvertTask())
    flow.edge("stage", "convert")
    proj.set_flow(flow)

    ImportFilesTask.find_task(proj).add_import_file(kernel)

    bambu = convert.ConvertTask.find_task(proj)
    bambu.set_bambu_memorychannels(2)
    bambu.set_bambu_experimentalsetup("BAMBU-BALANCED-MP")

    assert proj.run()

    assert proj.find_result("v", step="convert") == \
        os.path.abspath("build/main_kernel/job0/convert/0/outputs/main_kernel.v")

    history = proj.history("job0")
    for metric in ("registers", "cellarea", "fmax"):
        assert history.get("metric", metric, step="convert", index="0") is not None
