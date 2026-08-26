# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
import pytest

import os.path

from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler import ASIC, Design, Flowgraph, StdCellLibrary
from siliconcompiler.tools.opensta import timing
from siliconcompiler.tools.opensta.open import OpenTask as OpenSTAOpen

from siliconcompiler.tools.opensta.check_library import CheckLibraryTask
from siliconcompiler.flows.checklibraryflow import CheckLibraryFlow
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.targets._utils import asic_target

from tools.inputimporter import ImporterTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(asic_gcd):
    flow = Flowgraph("testflow")
    flow.node("version", timing.TimingTask())
    asic_gcd.set_flow(flow)

    node = SchedulerNode(asic_gcd, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_opensta(datadir):
    design = Design("testdesign")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("foo")
        design.add_file(os.path.join("lec", "foo.vg"))
    with design.active_dataroot("root"), design.active_fileset("sdc"):
        design.add_file(os.path.join("lec", "foo.sdc"))
    proj = ASIC(design)
    proj.add_fileset(["rtl", "sdc"])
    freepdk45_demo(proj)

    flow = Flowgraph("timing")
    flow.node("opensta", timing.TimingTask())
    proj.set_flow(flow)

    # Check that OpenSTA ran successfully
    assert proj.run()

    # Check that the setup and hold slacks are the expected values.
    assert proj.history("job0").get('metric', 'setupslack', step='opensta', index='0') == -0.220
    assert proj.history("job0").get('metric', 'holdslack', step='opensta', index='0') == 0.050

    # A single scenario duplicates the combined reports, so none are written
    assert not os.path.exists(
        os.path.join("build", "testdesign", "job0", "opensta", "0",
                     "reports", "timing", "scenarios"))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_opensta_scenario_reports(datadir):
    '''Per-scenario timing reports are only written when more than one scenario exists.'''
    design = Design("testdesign")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("foo")
        design.add_file(os.path.join("lec", "foo.vg"))
    with design.active_dataroot("root"), design.active_fileset("sdc"):
        design.add_file(os.path.join("lec", "foo.sdc"))
    proj = ASIC(design)
    proj.add_fileset(["rtl", "sdc"])
    freepdk45_demo(proj)

    # freepdk45_demo defines only "typical"; add a second scenario so the
    # per-scenario reports are generated.
    scenario = proj.constraint.timing.make_scenario("extra")
    scenario.add_libcorner(["typical", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold"])

    flow = Flowgraph("timing")
    flow.node("opensta", timing.TimingTask())
    proj.set_flow(flow)

    assert proj.run()

    reports = os.path.join("build", "testdesign", "job0", "opensta", "0",
                           "reports", "timing", "scenarios")
    # One directory per corner, each holding the same report set. The corner is repeated in
    # the file name so the reports stay unique if gathered into one place.
    assert set(os.listdir(reports)) == {"typical", "extra"}
    for corner in ("typical", "extra"):
        expected = set()
        for delay in ("setup", "hold"):
            for variant in ("", "topN.", "failing.", "endpoints."):
                expected.add(f"{delay}.{corner}.{variant}rpt")
            expected.add(f"worst_slack.{delay}.{corner}.rpt")
            expected.add(f"total_negative_slack.{delay}.{corner}.rpt")
        for variant in ("", "topN."):
            expected.add(f"unconstrained.{corner}.{variant}rpt")

        corner_dir = os.path.join(reports, corner)
        assert set(os.listdir(corner_dir)) == expected

        # The reports must have content, not just exist
        for report in expected:
            assert os.path.getsize(os.path.join(corner_dir, report)) > 0, f"{corner}/{report}"

    # The section banner must name every per-corner report that gets written, so the log
    # section stays one block instead of announcing files after the combined output.
    written = set()
    for corner in os.listdir(reports):
        for report in os.listdir(os.path.join(reports, corner)):
            written.add(f"reports/timing/scenarios/{corner}/{report}")

    logfile = os.path.join("build", "testdesign", "job0", "opensta", "0", "opensta.log")
    prefix = "== report: reports/timing/scenarios/"
    with open(logfile) as f:
        announced = [line.strip()[len("== report: "):] for line in f
                     if line.startswith(prefix)]

    # Kept as a list so a report announced twice is caught rather than deduplicated away
    assert len(announced) == len(set(announced))
    assert set(announced) == written

    # Metrics are still recorded, and now cite the per-scenario reports
    assert proj.history("job0").get('metric', 'setupslack', step='opensta', index='0') == -0.220
    assert proj.history("job0").get('metric', 'holdslack', step='opensta', index='0') == 0.050


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_opensta_sdf(datadir):
    design = Design("testdesign")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("foo")
        design.add_file(os.path.join("lec", "foo.vg"))
    with design.active_dataroot("root"), design.active_fileset("sdc"):
        design.add_file(os.path.join("lec", "foo.sdc"))
    proj = ASIC(design)
    proj.add_fileset(["rtl", "sdc"])
    freepdk45_demo(proj)

    flow = Flowgraph("timing")
    flow.node('import', ImporterTask())
    flow.node("opensta", timing.TimingTask())
    flow.edge('import', 'opensta')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).set("var", "input_files",
                                     os.path.join(datadir, 'lec', 'foo.typical.sdf'))

    # Check that OpenSTA ran successfully
    assert proj.run()

    # Check that the setup and hold slacks are the expected values.
    assert proj.history("job0").get('metric', 'setupslack', step='opensta', index='0') == -0.890
    assert proj.history("job0").get('metric', 'holdslack', step='opensta', index='0') == 0.020


def test_opensta_parameter_top_n_paths():
    task = timing.TimingTask()
    task.set_opensta_topnpaths(5)
    assert task.get("var", "top_n_paths") == 5
    task.set_opensta_topnpaths(10, step='timing', index='1')
    assert task.get("var", "top_n_paths", step='timing', index='1') == 10
    assert task.get("var", "top_n_paths") == 5


def test_opensta_parameter_unique_path_groups_per_clock():
    task = timing.TimingTask()
    task.set_opensta_uniquepathgroupsperclock(True)
    assert task.get("var", "unique_path_groups_per_clock") is True
    task.set_opensta_uniquepathgroupsperclock(False, step='timing', index='1')
    assert task.get("var", "unique_path_groups_per_clock", step='timing', index='1') is False
    assert task.get("var", "unique_path_groups_per_clock") is True


def test_opensta_parameter_timing_mode():
    task = timing.TimingTask()
    task.set_opensta_timingmode('min')
    assert task.get("var", "timing_mode") == 'min'
    task.set_opensta_timingmode('max', step='timing', index='1')
    assert task.get("var", "timing_mode", step='timing', index='1') == 'max'
    assert task.get("var", "timing_mode") == 'min'


def test_opensta_parameter_write_sdf():
    task = timing.TimingTask()
    task.set_opensta_writesdf(True)
    assert task.get("var", "write_sdf") is True
    task.set_opensta_writesdf(False, step='timing', index='1')
    assert task.get("var", "write_sdf", step='timing', index='1') is False
    assert task.get("var", "write_sdf") is True


def test_opensta_parameter_write_liberty():
    task = timing.TimingTask()
    task.set_opensta_writeliberty(True)
    assert task.get("var", "write_liberty") is True
    task.set_opensta_writeliberty(False, step='timing', index='1')
    assert task.get("var", "write_liberty", step='timing', index='1') is False
    assert task.get("var", "write_liberty") is True


def test_opensta_parameter_skip_report():
    task = timing.TimingTask()
    task.add_opensta_skipreport('clock_skew')
    assert task.get("var", "skip_reports") == ['clock_skew']
    task.add_opensta_skipreport(['setup', 'hold'], step='timing', index='1')
    assert task.get("var", "skip_reports", step='timing', index='1') == ['setup', 'hold']
    assert task.get("var", "skip_reports") == ['clock_skew']
    task.add_opensta_skipreport('fmax', clobber=True)
    assert task.get("var", "skip_reports") == ['fmax']


def test_opensta_parameter_skip_report_wildcard():
    task = timing.TimingTask()
    task.add_opensta_skipreport('*skew*')
    assert task.get("var", "skip_reports") == ['clock_skew']
    with pytest.raises(ValueError,
                       match="Report type pattern 'nomatch\\*' did not match any supported"):
        task.add_opensta_skipreport('nomatch*')


def test_opensta_reports_computed_at_setup():
    proj = ASIC(Design("testdesign"))
    with proj.design.active_fileset("rtl"):
        proj.design.set_topmodule("top")
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node("timing", timing.TimingTask())
    proj.set_flow(flow)

    task = timing.TimingTask.find_task(proj)
    task.add_opensta_skipreport(['power', 'design_stats'])

    with task.runtime(SchedulerNode(proj, "timing", "0")) as runtask:
        runtask.setup()

    reports = set(task.get("var", "reports", step="timing", index="0"))
    assert reports == set(timing.TimingTaskBase.REPORT_TYPES) - {'power', 'design_stats'}


def test_timing_write_sdf_and_liberty():
    """Test that both write_sdf and write_liberty can be enabled together."""
    design = Design("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("test")

    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    # Create flow with timing task
    flow = Flowgraph("test_flow")
    flow.node("timing", timing.TimingTask())
    proj.set_flow(flow)

    # Create a scenario
    scenario = proj.constraint.timing.make_scenario("testcorner")
    scenario.add_libcorner(["typical", "generic"])
    scenario.set_pexcorner("typical")

    # Enable both
    task = timing.TimingTask.find_task(proj)
    task.set("var", "write_sdf", True, step="timing", index="0")
    task.set("var", "write_liberty", True, step="timing", index="0")

    node = SchedulerNode(proj, step='timing', index='0')
    with node.runtime():
        node.setup()

        # Verify both file types are added
        outputs = node.task.get("output")
        assert "test.testcorner.sdf" in outputs, f"Expected testcorner.sdf in {outputs}"
        assert "test.testcorner.lib" in outputs, f"Expected testcorner.lib in {outputs}"


def test_timing_liberty_files_required():
    # Regression guard (P1): per-corner liberty files read by sc_timing.tcl must be
    # declared required so they are hashed (cache) and copied (remote runs).
    design = Design("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("test")

    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("test_flow")
    flow.node("timing", timing.TimingTask())
    proj.set_flow(flow)

    scenario = proj.constraint.timing.make_scenario("testcorner")
    scenario.add_libcorner(["typical"])
    scenario.set_pexcorner("typical")

    # mirror the run path: _init_run() populates asic,asiclib from mainlib before
    # node setup, which is when the liberty requires are declared.
    proj._init_run()

    node = SchedulerNode(proj, step='timing', index='0')
    with node.runtime():
        assert node.setup() is True
        requires = node.task.get("require")

    assert any("asic,libcornerfileset,typical," in r for r in requires), requires
    assert any(r.endswith("file,liberty") for r in requires), requires


def test_timing_mode_unknown_is_reported():
    # Regression guard: the check for an undefined mode called get_modes(), which
    # does not exist, so setting timing_mode raised AttributeError instead.
    design = Design("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("test")

    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("test_flow")
    flow.node("timing", timing.TimingTask())
    proj.set_flow(flow)

    task = timing.TimingTask.find_task(proj)
    task.set("var", "timing_mode", "nosuchmode", step="timing", index="0")

    proj._init_run()

    node = SchedulerNode(proj, step="timing", index="0")
    with node.runtime():
        with pytest.raises(LookupError, match="nosuchmode is not a defined mode"):
            node.setup()


def test_timing_mode_sdcfileset_is_per_node(tmp_path):
    # Regression guard: sdcfileset is PerNode.OPTIONAL and sc_manifest.tcl carries
    # the value resolved for the running node, so declaring the global value here
    # would hash and copy files sc_timing.tcl never reads.
    sdc = tmp_path / "mode.sdc"
    sdc.write_text("create_clock -name clk -period 10 [get_ports clk]\n")

    design = Design("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("test")
    with design.active_fileset("globalsdc"):
        design.add_file(str(sdc))
    with design.active_fileset("nodesdc"):
        design.add_file(str(sdc))

    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("test_flow")
    flow.node("timing", timing.TimingTask())
    proj.set_flow(flow)

    mode = proj.constraint.timing.make_mode("func")
    mode.add_sdcfileset(design, "globalsdc")
    mode.add_sdcfileset(design, "nodesdc", clobber=True, step="timing", index="0")

    scenario = proj.constraint.timing.make_scenario("testcorner")
    scenario.add_libcorner(["typical"])
    scenario.set_pexcorner("typical")
    scenario.set_mode("func")

    task = timing.TimingTask.find_task(proj)
    task.set("var", "timing_mode", "func", step="timing", index="0")

    proj._init_run()

    node = SchedulerNode(proj, step="timing", index="0")
    with node.runtime():
        assert node.setup() is True
        requires = node.task.get("require")

    assert "library,test,fileset,nodesdc,file,sdc" in requires, requires
    assert "library,test,fileset,globalsdc,file,sdc" not in requires, requires


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.parametrize("pdk", (
        pytest.param("freepdk45", marks=pytest.mark.quick),
        "asap7",
        "gf180",
        "ihp130",
        "skywater130"))
def test_check_library(pdk):
    # check_library reads the target's timing libraries and validates the
    # standard-cell tool setup (yosys/openroad helper cells and pins). A clean
    # run (zero errors) means the library setup is valid for that PDK; any
    # misconfiguration is emitted as an [ERROR] which halts the run.
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = ASIC(design)
    proj.add_fileset("rtl")
    asic_target(proj, pdk)
    proj.set_flow(CheckLibraryFlow())

    assert proj.run()
    assert proj.history("job0").get("metric", "errors", step="check", index="0") == 0


def test_check_library_required_keys():
    # Regression guard: the per-corner liberty files and the yosys/openroad
    # setup keys read by sc_check_library.tcl must be declared required so they
    # are hashed (cache) and copied (remote runs).
    design = Design("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("test")

    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("test_flow")
    flow.node("check", CheckLibraryTask())
    proj.set_flow(flow)

    # mirror the run path: _init_run() populates asic,asiclib from mainlib before
    # node setup, which is when the required keys are declared.
    proj._init_run()

    node = SchedulerNode(proj, step="check", index="0")
    with node.runtime():
        assert node.setup() is True
        requires = node.task.get("require")

    assert any(r.endswith("file,liberty") for r in requires), requires
    assert any(r.endswith("tool,yosys,driver_cell") for r in requires), requires
    assert any(r.endswith("tool,openroad,tiehigh_cell") for r in requires), requires


def _ccs_project(delaymodel="ccs"):
    '''freepdk45 with its NLDM liberty also registered under the ``ccs`` model.

    lambdapdk ships no CCS liberty today, so re-registering the NLDM fileset is
    what makes the ``(corner, "ccs")`` lookup resolve. That is enough to exercise
    the driver, and enough for OpenSTA itself: ``prima`` falls back to the default
    calculator for any arc whose liberty has no CCS waveforms.
    '''
    design = Design("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("test")

    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)
    proj.get_library("nangate45").add_asic_libcornerfileset(
        "typical", "ccs", "models.timing.nldm")
    proj.set_asic_delaymodel(delaymodel)
    return proj


def test_timing_ccs_liberty_files_required():
    # The ccs libcorner fileset must be the one declared required when the target
    # selects the ccs delay model.
    proj = _ccs_project()

    flow = Flowgraph("test_flow")
    flow.node("timing", timing.TimingTask())
    proj.set_flow(flow)

    proj._init_run()

    node = SchedulerNode(proj, step="timing", index="0")
    with node.runtime():
        assert node.setup() is True
        requires = node.task.get("require")

    assert any("asic,libcornerfileset,typical,ccs" in r for r in requires), requires
    assert not any("asic,libcornerfileset,typical,nldm" in r for r in requires), requires


def test_timing_unsupported_delaymodel():
    # OpenSTA reads liberty, so it can only be pointed at nldm or ccs filesets;
    # anything else must fail setup instead of feeding it unreadable files.
    proj = _ccs_project(delaymodel="ecsm")

    flow = Flowgraph("test_flow")
    flow.node("timing", timing.TimingTask())
    proj.set_flow(flow)

    proj._init_run()

    node = SchedulerNode(proj, step="timing", index="0")
    with node.runtime():
        with pytest.raises(ValueError,
                           match=r"^ecsm is not a supported delay model, "
                                 r"supported delay models are: nldm, ccs$"):
            node.setup()


def test_check_library_unsupported_delaymodel():
    proj = _ccs_project(delaymodel="nldm-bin")

    flow = Flowgraph("test_flow")
    flow.node("check", CheckLibraryTask())
    proj.set_flow(flow)

    proj._init_run()

    node = SchedulerNode(proj, step="check", index="0")
    with node.runtime():
        with pytest.raises(ValueError,
                           match=r"^nldm-bin is not a supported delay model, "
                                 r"supported delay models are: nldm, ccs$"):
            node.setup()


def _ccs_chain_project(datadir, delaymodel):
    '''A buffer/inverter chain timed against the ASAP7 CCS liberty fixture.

    The fixture carries the NLDM tables and the CCS output_current tables in the
    same file, and it is registered under both delay models, so the delay
    calculator is the only thing that differs between the two runs.

    freepdk45_demo supplies the surrounding project (PDK, timing scenario); the
    standard cell library it brings is replaced outright, since OpenSTA timing
    reads nothing from the PDK.
    '''
    design = Design("chain")
    design.set_dataroot("ccs", os.path.join(datadir, "ccs"))
    with design.active_dataroot("ccs"), design.active_fileset("rtl"):
        design.set_topmodule("chain")
        design.add_file("chain.vg")
    with design.active_dataroot("ccs"), design.active_fileset("sdc"):
        design.add_file("chain.sdc")

    lib = StdCellLibrary("asap7ccs")
    lib.set_dataroot("ccs", os.path.join(datadir, "ccs"))
    with lib.active_dataroot("ccs"), lib.active_fileset("models.timing"):
        lib.add_file("asap7sc7p5t_INVBUF_RVT_FF_ccs.lib.gz")
        lib.add_asic_libcornerfileset("typical", "nldm")
        lib.add_asic_libcornerfileset("typical", "ccs")

    proj = ASIC(design)
    proj.add_fileset(["rtl", "sdc"])
    freepdk45_demo(proj)
    proj.set_mainlib(lib)
    proj.add_asiclib(lib, clobber=True)
    proj.set_asic_delaymodel(delaymodel)

    flow = Flowgraph("timing")
    flow.node("import", ImporterTask())
    flow.node("opensta", timing.TimingTask())
    flow.edge("import", "opensta")
    proj.set_flow(flow)

    # prima needs a parasitic network on the driver pin; with nothing annotated it
    # falls back to the default calculator for every arc and the two delay models
    # come out identical.
    ImporterTask.find_task(proj).set(
        "var", "input_files", os.path.join(datadir, "ccs", "chain.typical.spef"))

    return proj


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_opensta_ccs_uses_prima(datadir):
    # The ccs delay model must switch OpenSTA to the prima delay calculator, and
    # prima must actually be the one computing the delays: reading a CCS liberty
    # under the default calculator parses the current source models and then
    # ignores them, which is indistinguishable from nldm.
    nldm = _ccs_chain_project(datadir, "nldm")
    assert nldm.run()
    nldm_slack = nldm.history("job0").get("metric", "setupslack",
                                          step="opensta", index="0")

    ccs = _ccs_chain_project(datadir, "ccs")
    ccs.set("option", "jobname", "ccs")
    assert ccs.run()
    ccs_slack = ccs.history("ccs").get("metric", "setupslack",
                                       step="opensta", index="0")

    with open(os.path.join("build", "chain", "ccs", "opensta", "0",
                           "opensta.log")) as log:
        assert "Using CCS delay calculation" in log.read()

    # Exact equality is the failure to catch: a prima that fell back, or a
    # set_delay_calculator line that stopped firing, reproduces the nldm number
    # to the digit rather than landing near it. The honest gap on an RC loaded
    # buffer chain is a couple of percent (0.09134 -> 0.08977), not a landslide.
    assert nldm_slack is not None and ccs_slack is not None
    assert ccs_slack != nldm_slack, \
        f"prima produced the nldm result ({ccs_slack}), so it fell back"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_opensta_open(datadir):
    '''The open task loads the netlist, corners and constraints, then stops.'''
    design = Design("testdesign")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("foo")
        design.add_file(os.path.join("lec", "foo.vg"))
    with design.active_dataroot("root"), design.active_fileset("sdc"):
        design.add_file(os.path.join("lec", "foo.sdc"))
    proj = ASIC(design)
    proj.add_fileset(["rtl", "sdc"])
    freepdk45_demo(proj)

    flow = Flowgraph("open")
    flow.node("open", OpenSTAOpen())
    proj.set_flow(flow)

    task = OpenSTAOpen.find_task(proj)
    task.set_showfilepath(os.path.join(datadir, "lec", "foo.vg"))
    # Without this the session is a breakpoint and the node never returns.
    task.set_showexit(True)

    assert proj.run()

    workdir = os.path.join("build", "testdesign", "job0", "open", "0")

    with open(os.path.join(workdir, "open.log")) as f:
        log = f.read()

    # showfilepath was copied into inputs/, not read from the rtl fileset
    assert os.path.isfile(os.path.join(workdir, "inputs", "foo.vg"))
    assert "Reading netlist verilog: inputs/foo.vg" in log
    # the rest of the timing context still comes from TimingTask's handling
    assert "Defining timing corners: typical" in log
    assert "NangateOpenCellLibrary_typical.lib" in log
    assert "foo.sdc" in log

    # ... and nothing is reported or written
    assert "SC_METRIC" not in log
    assert not os.path.exists(os.path.join(workdir, "reports", "timing"))
    # the node manifest and nothing else -- no design artifacts
    assert os.listdir(os.path.join(workdir, "outputs")) == ["testdesign.pkg.json"]
