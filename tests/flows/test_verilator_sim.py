import os
import subprocess

import pytest

import siliconcompiler

@pytest.mark.eda
def test_basic(scroot, datadir):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.set('input', 'rtl', 'verilog', v_src)
    c_src = os.path.join(datadir, 'heartbeat_tb.cpp')
    chip.set('input', 'hll', 'c', c_src)

    chip.set('option', 'mode', 'sim')

    # Basic Verilator compilation flow
    flow = 'verilator_compile'
    chip.node(flow, 'import', 'surelog')
    chip.node(flow, 'compile', 'verilator')
    chip.edge(flow, 'import', 'compile')
    chip.set('option', 'flow', flow)

    chip.run()

    exe_path = chip.find_result('vexe', step='compile')

    proc = subprocess.run([exe_path], stdout=subprocess.PIPE)
    output = proc.stdout.decode('utf-8')
    print(output)

    assert output == 'SUCCESS\n'
