# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest

import os.path

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.icarus import compile


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_compile(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("compile", compile.CompileTask())
    proj.set_flow(flow)

    assert proj.run()

    # check that compilation succeeded
    assert proj.find_result('vpp', step='compile') == \
        os.path.abspath("build/gcd/job0/compile/0/outputs/gcd.vpp")


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", compile.CompileTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_runtime_args(heartbeat_design):
    proj = Project(heartbeat_design)
    heartbeat_design.set_param("N", "8", "rtl")
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", compile.CompileTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get_runtime_arguments() == [
            '-o', 'outputs/heartbeat.vpp',
            '-s', 'heartbeat',
            '-Pheartbeat.N=8',
            '-DSILICONCOMPILER_TRACE_FILE="reports/heartbeat.vcd"',
            heartbeat_design.get_file("rtl", "verilog")[0]]
