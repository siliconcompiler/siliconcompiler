import pytest

import os.path

from siliconcompiler import Project, FlowgraphSchema, DesignSchema
from siliconcompiler.tools.slang.elaborate import Elaborate
from siliconcompiler.tools.verilator import lint, compile
from siliconcompiler.scheduler import SchedulerNode


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_lint_post_slang(heartbeat_design):
    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
    flow.node("elaborate", Elaborate())
    flow.node("lint", lint.LintTask())
    flow.edge("elaborate", "lint")
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get("record", "toolargs", step="lint", index="0") == \
        "-sv --top-module heartbeat inputs/heartbeat.v --lint-only --no-timing"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_compile(heartbeat_design, datadir, run_cli):
    with heartbeat_design.active_fileset("tb_test_cpp"):
        heartbeat_design.add_file(os.path.join(datadir, 'verilator', 'heartbeat_tb.cpp'))

    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")
    proj.add_fileset("tb_test_cpp")

    flow = FlowgraphSchema("testflow")
    flow.node("elaborate", Elaborate())
    flow.node("compile", compile.CompileTask())
    flow.edge("elaborate", "compile")
    proj.set_flow(flow)

    assert proj.get_task(filter=compile.CompileTask).set("var", "cflags", '-DREQUIRED_FROM_USER')
    assert proj.get_task(filter=compile.CompileTask).set(
        "var", "cincludes", os.path.join(datadir, 'verilator', 'include'))

    assert proj.run()

    exe_path = proj.find_result('vexe', step='compile')
    assert os.path.exists(exe_path)
    proc = run_cli(exe_path)

    assert proc.stdout == 'SUCCESS\n'


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_assert(heartbeat_design, datadir, run_cli):
    with heartbeat_design.active_fileset("assert"):
        heartbeat_design.set_topmodule("heartbeat")
        heartbeat_design.add_file(os.path.join(datadir, 'verilator', 'assert.v'))
    with heartbeat_design.active_fileset("tb_test_cpp"):
        heartbeat_design.add_file(os.path.join(datadir, 'verilator', 'heartbeat_tb.cpp'))

    proj = Project(heartbeat_design)
    proj.add_fileset("assert")
    proj.add_fileset("tb_test_cpp")

    flow = FlowgraphSchema("testflow")
    flow.node("elaborate", Elaborate())
    flow.node("compile", compile.CompileTask())
    flow.edge("elaborate", "compile")
    proj.set_flow(flow)

    assert proj.get_task(filter=compile.CompileTask).set("var", "enable_assert", True)
    assert proj.get_task(filter=compile.CompileTask).set("var", "cflags", '-DREQUIRED_FROM_USER')
    assert proj.get_task(filter=compile.CompileTask).set(
        "var", "cincludes", os.path.join(datadir, 'verilator', 'include'))

    assert proj.run()

    exe_path = proj.find_result('vexe', step='compile')
    assert os.path.exists(exe_path)

    proc = run_cli(exe_path, retcode=-6)
    assert "Assertion failed in TOP.heartbeat: 'assert' failed." in \
        proc.stdout


def test_config_files_from_libs(gcd_design):
    with open('test.cfg', 'w') as f:
        f.write('test')

    dep_design = DesignSchema("libdep")
    with dep_design.active_fileset("config"):
        dep_design.add_file('test.cfg', filetype="config")

    with gcd_design.active_fileset("rtl"):
        gcd_design.add_depfileset(dep_design, "config")

    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
    flow.node("lint", lint.LintTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "lint", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 7
        del arguments[4]
        assert arguments == [
            '-sv', '--top-module', 'gcd',
            os.path.abspath("test.cfg"),
            '--lint-only', '--no-timing']


def test_random_reset(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
    flow.node("compile", compile.CompileTask())
    proj.set_flow(flow)

    assert proj.get_task(filter=compile.CompileTask).set("var", "initialize_random", True)

    node = SchedulerNode(proj, "compile", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 13
        del arguments[9]
        del arguments[3]
        assert arguments == [
            '-sv', '--top-module', 'gcd',
            '--x-assign', 'unique',
            '--exe', '--build',
            '-j',
            '--cc', '-o', '../outputs/gcd.vexe']


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
    flow.node("version", compile.CompileTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_lintflow(heartbeat_design):
    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
    flow.node("lint", lint.LintTask())
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='lint', index='0') == 0
    assert proj.history("job0").get('metric', 'warnings', step='lint', index='0') == 0
