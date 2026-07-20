# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest

from siliconcompiler import Design, Project, Flowgraph
from siliconcompiler.flows.formalflow import PropertyCheckFlow, PropertyCheckMode
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.sby import bmc, cover, prove


def test_task_modes():
    assert bmc.BMCTask().mode() == "bmc"
    assert cover.CoverTask().mode() == "cover"
    assert prove.ProveTask().mode() == "prove"


def test_parameters():
    task = bmc.BMCTask()

    task.set_sby_depth(45)
    assert task.get("var", "depth") == 45

    # bitwuzla is the default; boolector is the other selectable engine
    assert task.get("var", "engine") == ["smtbmc bitwuzla"]

    # without clobber a new engine line is appended
    task.add_sby_engine("smtbmc boolector")
    assert task.get("var", "engine") == ["smtbmc bitwuzla", "smtbmc boolector"]

    # with clobber the engine list is replaced
    task.add_sby_engine("smtbmc boolector", clobber=True)
    assert task.get("var", "engine") == ["smtbmc boolector"]


def test_propertycheckflow_modes():
    def steps(flow):
        return sorted({step for step, index in flow.get_nodes()})

    bmc_m, prove_m, cover_m = (PropertyCheckMode.BMC,
                               PropertyCheckMode.PROVE,
                               PropertyCheckMode.COVER)

    # each selected mode becomes a parallel node named after it
    assert steps(PropertyCheckFlow()) == ["bmc"]
    assert steps(PropertyCheckFlow(modes=bmc_m | cover_m)) == ["bmc", "cover"]
    assert steps(PropertyCheckFlow(modes=bmc_m | prove_m | cover_m)) == ["bmc", "cover", "prove"]

    with pytest.raises(ValueError, match=r"^requires at least one mode$"):
        PropertyCheckFlow(modes=bmc_m & cover_m)


def test_sby_file_generation(gcd_design, monkeypatch):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("formal", bmc.BMCTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "formal", "0")
    with node.runtime():
        assert node.setup() is True

        node.task.setup_work_directory(node.workdir)
        monkeypatch.chdir(node.workdir)

        node.task.pre_process()

        sby_file = "gcd.sby"
        assert os.path.exists(sby_file)
        with open(sby_file) as f:
            job = f.read().splitlines()

    assert job[0] == "[options]"
    assert job[1] == "mode bmc"
    assert job[2] == "depth 20"
    assert job[3] == ""
    assert job[4] == "[engines]"
    assert job[5] == "smtbmc bitwuzla"
    assert job[6] == ""
    assert job[7] == "[script]"

    # sources are referenced by their original path, then elaborated
    sources = gcd_design.get_file(fileset="rtl", filetype="verilog")
    script = job[8:]
    for i, src in enumerate(sources):
        assert script[i] == f"read_verilog -formal -sv {src}"
    assert script[len(sources)] == "prep -top gcd"


def test_sby_params_and_timeout(gcd_design, monkeypatch):
    gcd_design.set("fileset", "rtl", "param", "N", "64")

    proj = Project(gcd_design)
    proj.add_fileset("rtl")
    proj.option.set_timeout(120)

    flow = Flowgraph("testflow")
    flow.node("formal", bmc.BMCTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "formal", "0")
    with node.runtime():
        assert node.setup() is True

        node.task.setup_work_directory(node.workdir)
        monkeypatch.chdir(node.workdir)

        node.task.pre_process()
        with open("gcd.sby") as f:
            job = f.read().splitlines()

    # node timeout is written into the [options] section
    assert job[3] == "timeout 120"
    # the design param becomes a chparam line after the read_verilog lines
    script = job[job.index("[script]") + 1:]
    sources = gcd_design.get_file(fileset="rtl", filetype="verilog")
    assert script[len(sources)] == "chparam -set N 64 gcd"


def test_runtime_args(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("formal", bmc.BMCTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "formal", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get_runtime_arguments() == [
            '-f',
            '-d', 'sby',
            'gcd.sby']


def test_pre_process_requires_sources(monkeypatch, tmp_path):
    # a fileset with a topmodule but no verilog/systemverilog sources
    design = Design("nosrc")
    design.set_dataroot("root", str(tmp_path))
    design.set_topmodule("nosrc", fileset="rtl")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("formal", bmc.BMCTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "formal", "0")
    with node.runtime():
        assert node.setup() is True

        node.task.setup_work_directory(node.workdir)
        monkeypatch.chdir(node.workdir)

        with pytest.raises(ValueError,
                           match=r"at least one verilog/systemverilog source file"):
            node.task.pre_process()


def _counter_project(datadir, modes, rtl="sby/counter.v"):
    design = Design("counter")
    design.set_dataroot("root", datadir)
    design.set_topmodule("counter", fileset="rtl")
    design.add_file(rtl, dataroot="root", fileset="rtl")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(PropertyCheckFlow(modes=modes))
    return proj


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", bmc.BMCTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_bmc_pass(datadir):
    proj = _counter_project(datadir, PropertyCheckMode.BMC)
    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='bmc', index='0') == 0

    with open("build/counter/job0/bmc/0/sby/status") as f:
        assert f.read().strip() == "PASS 0 0"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_bmc_fail_produces_trace(datadir):
    # counter_fail.v tightens the bound so the assertion is violated
    proj = _counter_project(datadir, PropertyCheckMode.BMC, rtl="sby/counter_fail.v")
    with pytest.raises(RuntimeError):
        proj.run()

    with open("build/counter/job0/bmc/0/sby/status") as f:
        assert f.read().strip() == "FAIL 2 0"

    # counterexample trace is preserved for debugging
    assert os.path.exists("build/counter/job0/bmc/0/reports/trace.vcd")


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_prove_pass(datadir):
    proj = _counter_project(datadir, PropertyCheckMode.PROVE)
    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='prove', index='0') == 0
