# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest

from siliconcompiler import Design, Project, Flowgraph
from siliconcompiler.flows.formalflow import FormalFlow
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

    # boolector is currently the only supported engine
    assert task.get("var", "engine") == ["smtbmc boolector"]

    # add_sby_engine replaces the list when clobbering
    task.add_sby_engine("smtbmc boolector", clobber=True)
    assert task.get("var", "engine") == ["smtbmc boolector"]


def test_formalflow_modes():
    assert FormalFlow().name == "formalflow-bmc"
    assert FormalFlow(mode="prove").name == "formalflow-prove"
    assert FormalFlow(mode="cover").name == "formalflow-cover"

    with pytest.raises(ValueError, match="Unsupported formal mode"):
        FormalFlow(mode="lint")


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
    assert job[5] == "smtbmc boolector"
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

    # node timeout is written into the job; params become chparam lines
    assert "timeout 120" in job
    assert "chparam -set N 64 gcd" in job


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


def _counter_project(datadir, mode, rtl="sby/counter.v"):
    design = Design("counter")
    design.set_dataroot("root", datadir)
    design.set_topmodule("counter", fileset="rtl")
    design.add_file(rtl, dataroot="root", fileset="rtl")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(FormalFlow(mode=mode))
    return proj


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_bmc_pass(datadir):
    proj = _counter_project(datadir, "bmc")
    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='formal', index='0') == 0

    # sby writes "<status> <count> <count>"; the first token is the verdict
    with open("build/counter/job0/formal/0/sby/status") as f:
        assert f.read().split()[0] == "PASS"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_bmc_fail_produces_trace(datadir):
    # counter_fail.v tightens the bound so the assertion is violated
    proj = _counter_project(datadir, "bmc", rtl="sby/counter_fail.v")
    with pytest.raises(RuntimeError):
        proj.run()

    with open("build/counter/job0/formal/0/sby/status") as f:
        assert f.read().split()[0] == "FAIL"

    # counterexample trace is preserved for debugging
    assert os.path.exists("build/counter/job0/formal/0/reports/trace.vcd")


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_prove_pass(datadir):
    proj = _counter_project(datadir, "prove")
    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='formal', index='0') == 0
