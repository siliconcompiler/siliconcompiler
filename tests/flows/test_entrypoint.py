import os

import pytest

import siliconcompiler

@pytest.mark.eda
def test_entrypoint(scroot):
    datadir = os.path.join(scroot, 'tests', 'data')
    chip = siliconcompiler.Chip('heartbeat')

    chip.add('input', 'verilog', os.path.join(datadir, 'heartbeat.v'))
    chip.add('input', 'verilog', os.path.join(datadir, 'heartbeat_top.v'))

    chip.set('option', 'entrypoint', 'heartbeat_top')

    chip.load_target('skywater130_demo')

    chip.run()

    assert chip.find_result('gds', step='export') is not None

    # If ['option', 'entrypoint'] didn't work, this test would just build
    # heartbeat, and the design would have half as many cells post-synthesis.
    assert chip.get('metric', 'syn', '0', 'cells') == 50
