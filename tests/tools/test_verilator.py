import os
import pytest

import siliconcompiler
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.verilator import lint, compile
from siliconcompiler.scheduler import SchedulerNode


@pytest.mark.eda
@pytest.mark.quick
def test_lint_post_surelog(scroot):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.input(v_src)

    flow = 'lint'
    chip.node(flow, 'import', parse)
    chip.node(flow, 'lint', lint)
    chip.edge(flow, 'import', 'lint')
    chip.set('option', 'flow', flow)

    assert chip.run()


@pytest.mark.eda
@pytest.mark.quick
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

    assert chip.run()

    exe_path = chip.find_result('vexe', step='compile')

    assert exe_path

    proc = run_cli(exe_path)

    assert proc.stdout == 'SUCCESS\n'


@pytest.mark.eda
@pytest.mark.quick
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

    assert chip.run()

    exe_path = chip.find_result('vexe', step='compile')

    assert exe_path

    proc = run_cli(exe_path, retcode=-6)

    assert "Assertion failed in TOP.heartbeat: 'assert' failed." in \
        proc.stdout


def test_config_files_from_libs():
    lib = siliconcompiler.Library('test_lib', auto_enable=True)
    lib.set('option', 'file', 'verilator_config', 'test.cfg')
    with open('test.cfg', 'w') as f:
        f.write('test')
    with open('test.v', 'w') as f:
        f.write('test')

    chip = siliconcompiler.Chip('test')
    chip.input('test.v')
    chip.use(lib)

    flow = 'verilator_compile'
    chip.node(flow, 'import', lint)
    chip.set('option', 'flow', flow)

    SchedulerNode(chip, "import", "0").setup()

    chip.set('arg', 'step', 'import')
    chip.set('arg', 'index', '0')

    assert os.path.abspath('test.cfg') in lint.runtime_options(chip)


@pytest.mark.nostrict
def test_random_reset():
    chip = siliconcompiler.Chip('test')
    chip.input('test.v')
    with open('test.v', 'w') as f:
        f.write('test')

    flow = 'verilator_compile'
    chip.node(flow, 'import', compile)
    chip.set('option', 'flow', flow)

    chip.set('tool', 'verilator', 'task', 'compile', 'var', 'initialize_random', True)

    SchedulerNode(chip, "import", "0").setup()

    chip.set('arg', 'step', 'import')
    chip.set('arg', 'index', '0')

    args = compile.runtime_options(chip)

    assert '--x-assign' in args
    assert 'unique' in args
