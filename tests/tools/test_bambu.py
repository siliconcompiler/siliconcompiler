import json
import os
import pytest
import re
import shutil

import os.path

from siliconcompiler import ASIC, Project, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.bambu import convert


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
    """bambu cannot simulate without one, so say so at setup rather than
    letting the run get most of the way there and fail."""
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
        with pytest.raises(ValueError, match="simulation needs a testbench"):
            node.setup()


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
