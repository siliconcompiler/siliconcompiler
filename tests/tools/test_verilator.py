import os
import pytest

import siliconcompiler
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.verilator import lint, compile


@pytest.mark.quick
@pytest.mark.eda
def test_lint_post_surelog(scroot):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.input(v_src)

    flow = 'lint'
    chip.node(flow, 'import', parse)
    chip.node(flow, 'lint', lint)
    chip.edge(flow, 'import', 'lint')
    chip.set('option', 'flow', flow)

    chip.run()


@pytest.mark.quick
@pytest.mark.eda
def test_compile(scroot, datadir, run_cli):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.input(v_src)
    c_src = os.path.join(datadir, 'verilator', 'heartbeat_tb.cpp')
    chip.input(c_src)
    vlt_cfg = os.path.join(datadir, 'verilator', 'config.vlt')
    chip.set('tool', 'verilator', 'task', 'compile', 'file', 'config', vlt_cfg)

    chip.add('tool', 'verilator', 'task', 'compile', 'var', 'cflags', '-DREQUIRED_FROM_USER')
    c_inc = os.path.join(datadir, 'verilator', 'include')
    chip.add('tool', 'verilator', 'task', 'compile', 'dir', 'cincludes', c_inc)

    # Basic Verilator compilation flow
    flow = 'verilator_compile'
    chip.node(flow, 'import', parse)
    chip.node(flow, 'compile', compile)
    chip.edge(flow, 'import', 'compile')
    chip.set('option', 'flow', flow)

    chip.run()

    exe_path = chip.find_result('vexe', step='compile')

    assert exe_path

    proc = run_cli(exe_path, stdout_to_pipe=True)

    assert proc.stdout.decode('utf-8') == 'SUCCESS\n'


@pytest.mark.quick
@pytest.mark.eda
def test_assert(scroot, datadir, run_cli):
    chip = siliconcompiler.Chip('heartbeat')
    chip.set('tool', 'verilator', 'task', 'compile', 'var', 'enable_assert', ['true'])

    v_src = os.path.join(scroot, 'tests', 'data', 'assert.v')
    chip.input(v_src)
    c_src = os.path.join(datadir, 'verilator', 'heartbeat_tb.cpp')
    chip.input(c_src)

    chip.add('tool', 'verilator', 'task', 'compile', 'var', 'cflags', '-DREQUIRED_FROM_USER')
    c_inc = os.path.join(datadir, 'verilator', 'include')
    chip.add('tool', 'verilator', 'task', 'compile', 'dir', 'cincludes', c_inc)

    # Basic Verilator compilation flow
    flow = 'verilator_compile'
    chip.node(flow, 'import', parse)
    chip.node(flow, 'compile', compile)
    chip.edge(flow, 'import', 'compile')
    chip.set('option', 'flow', flow)

    chip.run()

    exe_path = chip.find_result('vexe', step='compile')

    assert exe_path

    proc = run_cli(exe_path, stdout_to_pipe=True, retcode=-6)

    assert "Assertion failed in TOP.heartbeat: 'assert' failed." in \
        proc.stdout.decode('utf-8')
