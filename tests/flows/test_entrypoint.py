import os

import pytest

import siliconcompiler
from siliconcompiler.targets import freepdk45_demo

@pytest.mark.eda
def test_entrypoint(scroot):
    datadir = os.path.join(scroot, 'tests', 'data')
    chip = siliconcompiler.Chip('heartbeat')

    chip.input(os.path.join(datadir, 'heartbeat.v'))
    chip.input(os.path.join(datadir, 'heartbeat_top.v'))

    chip.set('option', 'entrypoint', 'heartbeat_top')

    chip.use(skywater130_demo)

    chip.run()

    assert chip.find_result('gds', step='export') is not None

    # If ['option', 'entrypoint'] didn't work, this test would just build
    # heartbeat, and the design would have half as many cells post-synthesis.
    assert chip.get('metric', 'syn', '0', 'cells') == 52
