import pytest

import os.path

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.tools.slang.elaborate import Elaborate
from siliconcompiler.tools.verilator import lint, compile
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler import utils


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_lint_post_slang(heartbeat_design):
    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("elaborate", Elaborate())
    flow.node("lint", lint.LintTask())
    flow.edge("elaborate", "lint")
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get("record", "toolargs", step="lint", index="0") == \
        "-sv --top-module heartbeat inputs/heartbeat.v --lint-only --no-timing"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_compile(heartbeat_design, datadir, run_cli):
    with heartbeat_design.active_fileset("tb_test_cpp"):
        heartbeat_design.add_file(os.path.join(datadir, 'verilator', 'heartbeat_tb.cpp'))

    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")
    proj.add_fileset("tb_test_cpp")

    flow = Flowgraph("testflow")
    flow.node("elaborate", Elaborate())
    flow.node("compile", compile.CompileTask())
    flow.edge("elaborate", "compile")
    proj.set_flow(flow)

    assert compile.CompileTask.find_task(proj).set("var", "cflags", '-DREQUIRED_FROM_USER')
    assert compile.CompileTask.find_task(proj).set(
        "var", "cincludes", os.path.join(datadir, 'verilator', 'include'))

    assert proj.run()

    exe_path = proj.find_result('vexe', step='compile')
    assert os.path.exists(exe_path)
    proc = run_cli(exe_path)

    assert proc.stdout == 'SUCCESS\n'


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_assert(heartbeat_design, datadir, run_cli):
    with heartbeat_design.active_fileset("assert"):
        heartbeat_design.set_topmodule("heartbeat")
        heartbeat_design.add_file(os.path.join(datadir, 'verilator', 'assert.v'))
    with heartbeat_design.active_fileset("tb_test_cpp"):
        heartbeat_design.add_file(os.path.join(datadir, 'verilator', 'heartbeat_tb.cpp'))

    proj = Project(heartbeat_design)
    proj.add_fileset("assert")
    proj.add_fileset("tb_test_cpp")

    flow = Flowgraph("testflow")
    flow.node("elaborate", Elaborate())
    flow.node("compile", compile.CompileTask())
    flow.edge("elaborate", "compile")
    proj.set_flow(flow)

    assert compile.CompileTask.find_task(proj).set("var", "enable_assert", True)
    assert compile.CompileTask.find_task(proj).set("var", "cflags", '-DREQUIRED_FROM_USER')
    assert compile.CompileTask.find_task(proj).set(
        "var", "cincludes", os.path.join(datadir, 'verilator', 'include'))

    assert proj.run()

    exe_path = proj.find_result('vexe', step='compile')
    assert os.path.exists(exe_path)

    proc = run_cli(exe_path, retcode=-6)
    assert "Assertion failed in TOP.heartbeat: 'assert' failed." in \
        proc.stdout


def test_config_files_from_libs(gcd_design):
    with open('test.vlt', 'w') as f:
        f.write('test')

    dep_design = Design("libdep")
    with dep_design.active_fileset("config"):
        dep_design.add_file('test.vlt')

    with gcd_design.active_fileset("rtl"):
        gcd_design.add_depfileset(dep_design, "config")

    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
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
            os.path.abspath("test.vlt"),
            '--lint-only', '--no-timing']


def test_random_reset(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("compile", compile.CompileTask())
    proj.set_flow(flow)

    assert compile.CompileTask.find_task(proj).set("var", "initialize_random", True)

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
@pytest.mark.timeout(300)
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


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_lintflow(heartbeat_design):
    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("lint", lint.LintTask())
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='lint', index='0') == 0
    assert proj.history("job0").get('metric', 'warnings', step='lint', index='0') == 0


def test_runtime_args(heartbeat_design, monkeypatch):
    proj = Project(heartbeat_design)
    heartbeat_design.set_param("N", "8", "rtl")
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", compile.CompileTask())
    proj.set_flow(flow)

    def limit_cpu(*args, **kwargs):
        return 2

    monkeypatch.setattr(utils, 'get_cores', limit_cpu)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get_runtime_arguments() == [
            '-sv',
            '--top-module', 'heartbeat',
            '-GN=8',
            heartbeat_design.get_file("rtl", "verilog")[0],
            '--exe',
            '--build',
            '-j', '2',
            '--cc',
            '-o', '../outputs/heartbeat.vexe']


def test_runtime_args_trace(heartbeat_design, monkeypatch):
    proj = Project(heartbeat_design)
    heartbeat_design.set_param("N", "8", "rtl")
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", compile.CompileTask())
    proj.set_flow(flow)
    compile.CompileTask.find_task(proj).set("var", "trace", True)

    def limit_cpu(*args, **kwargs):
        return 2

    monkeypatch.setattr(utils, 'get_cores', limit_cpu)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get_runtime_arguments() == [
            '-sv',
            '--top-module', 'heartbeat',
            '-GN=8',
            heartbeat_design.get_file("rtl", "verilog")[0],
            '--exe',
            '--build',
            '-j', '2',
            '--cc',
            '-o', '../outputs/heartbeat.vexe',
            '--trace',
            '-CFLAGS', '\'-DSILICONCOMPILER_TRACE_DIR="reports"\' '
                       '\'-DSILICONCOMPILER_TRACE_FILE="reports/heartbeat.vcd"\'']


def test_verilator_parameter_mode():
    task = compile.CompileTask()
    task.set_verilator_mode('systemc')
    assert task.get("var", "mode") == 'systemc'
    task.set_verilator_mode('cc', step='compile', index='1')
    assert task.get("var", "mode", step='compile', index='1') == 'cc'
    assert task.get("var", "mode") == 'systemc'


def test_verilator_parameter_trace():
    task = compile.CompileTask()
    task.set_verilator_trace(True)
    assert task.get("var", "trace") is True
    task.set_verilator_trace(False, step='compile', index='1')
    assert task.get("var", "trace", step='compile', index='1') is False
    assert task.get("var", "trace") is True


def test_verilator_parameter_trace_type():
    task = compile.CompileTask()
    task.set_verilator_tracetype('fst')
    assert task.get("var", "trace_type") == 'fst'
    task.set_verilator_tracetype('vcd', step='compile', index='1')
    assert task.get("var", "trace_type", step='compile', index='1') == 'vcd'
    assert task.get("var", "trace_type") == 'fst'


def test_verilator_parameter_cincludes():
    task = compile.CompileTask()
    task.add_verilator_cincludes('include_dir')
    assert task.get("var", "cincludes") == ['include_dir']
    task.add_verilator_cincludes('another_dir')
    assert task.get("var", "cincludes") == ['include_dir', 'another_dir']
    task.add_verilator_cincludes('other_dir', step='compile', index='1')
    assert task.get("var", "cincludes", step='compile', index='1') == ['other_dir']
    assert task.get("var", "cincludes") == ['include_dir', 'another_dir']
    task.add_verilator_cincludes(['new_dir1', 'new_dir2'], clobber=True)
    assert task.get("var", "cincludes") == ['new_dir1', 'new_dir2']


def test_verilator_parameter_cflags():
    task = compile.CompileTask()
    task.add_verilator_cflags('-g')
    assert task.get("var", "cflags") == ['-g']
    task.add_verilator_cflags('-O2')
    assert task.get("var", "cflags") == ['-g', '-O2']
    task.add_verilator_cflags('-O3', step='compile', index='1')
    assert task.get("var", "cflags", step='compile', index='1') == ['-O3']
    assert task.get("var", "cflags") == ['-g', '-O2']
    task.add_verilator_cflags(['-Wall', '-Wextra'], clobber=True)
    assert task.get("var", "cflags") == ['-Wall', '-Wextra']


def test_verilator_parameter_ldflags():
    task = compile.CompileTask()
    task.add_verilator_ldflags('-lm')
    assert task.get("var", "ldflags") == ['-lm']
    task.add_verilator_ldflags('-lrt')
    assert task.get("var", "ldflags") == ['-lm', '-lrt']
    task.add_verilator_ldflags('-lpthread', step='compile', index='1')
    assert task.get("var", "ldflags", step='compile', index='1') == ['-lpthread']
    assert task.get("var", "ldflags") == ['-lm', '-lrt']
    task.add_verilator_ldflags(['-lstdc++', '-lz'], clobber=True)
    assert task.get("var", "ldflags") == ['-lstdc++', '-lz']


def test_verilator_parameter_pins_bv():
    task = compile.CompileTask()
    task.set_verilator_pinsbv(8)
    assert task.get("var", "pins_bv") == 8
    task.set_verilator_pinsbv(16, step='compile', index='1')
    assert task.get("var", "pins_bv", step='compile', index='1') == 16
    assert task.get("var", "pins_bv") == 8


def test_verilator_parameter_initialize_random():
    task = compile.CompileTask()
    task.set_verilator_initializerandom(True)
    assert task.get("var", "initialize_random") is True
    task.set_verilator_initializerandom(False, step='compile', index='1')
    assert task.get("var", "initialize_random", step='compile', index='1') is False
    assert task.get("var", "initialize_random") is True
