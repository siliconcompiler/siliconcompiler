# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest
import shutil

import os.path

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

    task.set_depth(45)
    assert task.get("var", "depth") == 45

    task.set_engine(["smtbmc boolector"])
    assert task.get("var", "engine") == ["smtbmc boolector"]

    task.set_timeout(120)
    assert task.get("var", "timeout") == 120

    task.set_toolroot("/opt/formal")
    assert task.get("var", "toolroot") == "/opt/formal"


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
            job = f.read()

        assert "mode bmc" in job
        assert "depth 20" in job
        assert "smtbmc bitwuzla" in job
        assert "prep -top gcd" in job
        for src in gcd_design.get_file(fileset="rtl", filetype="verilog"):
            assert f"read_verilog -formal -sv {os.path.basename(src)}" in job
            assert f"{os.path.basename(src)} {src}" in job


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


PASS_COUNTER = """
module counter (
    input clk,
    output reg [5:0] count
);
    initial count = 0;

    always @(posedge clk) begin
        if (count == 15)
            count <= 0;
        else
            count <= count + 1'b1;
    end

`ifdef FORMAL
    always @(posedge clk)
        assert (count < 32);
`endif
endmodule
"""


def _counter_project(mode):
    design = Design("counter")
    design.set_dataroot("testroot", os.getcwd())
    design.set_topmodule("counter", fileset="rtl")
    design.add_file("counter.v", dataroot="testroot", fileset="rtl")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(FormalFlow(mode=mode))
    return proj


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("sby") is None or shutil.which("bitwuzla") is None,
                    reason="sby/bitwuzla are not available")
def test_bmc_pass():
    with open("counter.v", "w") as f:
        f.write(PASS_COUNTER)

    proj = _counter_project("bmc")
    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='formal', index='0') == 0

    with open("build/counter/job0/formal/0/sby/status") as f:
        assert f.read().startswith("PASS")


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("sby") is None or shutil.which("bitwuzla") is None,
                    reason="sby/bitwuzla are not available")
def test_bmc_fail_produces_trace():
    # assertion bound is violated when the counter reaches 8
    with open("counter.v", "w") as f:
        f.write(PASS_COUNTER.replace("count < 32", "count < 8"))

    proj = _counter_project("bmc")
    with pytest.raises(RuntimeError):
        proj.run()

    with open("build/counter/job0/formal/0/sby/status") as f:
        assert f.read().startswith("FAIL")

    # counterexample trace is preserved for debugging
    assert os.path.exists("build/counter/job0/formal/0/reports/trace.vcd")


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("sby") is None or shutil.which("bitwuzla") is None,
                    reason="sby/bitwuzla are not available")
def test_prove_pass():
    with open("counter.v", "w") as f:
        f.write(PASS_COUNTER)

    proj = _counter_project("prove")
    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='formal', index='0') == 0
