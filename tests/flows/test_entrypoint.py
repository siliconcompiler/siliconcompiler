import os

import pytest

import siliconcompiler
from siliconcompiler.targets import skywater130_demo


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_entrypoint(scroot):
    datadir = os.path.join(scroot, 'tests', 'data')
    chip = siliconcompiler.Chip('heartbeat')

    chip.input(os.path.join(datadir, 'heartbeat.v'))
    chip.input(os.path.join(datadir, 'heartbeat_top.v'))

    chip.set('option', 'entrypoint', 'heartbeat_top')

    chip.use(skywater130_demo)
    chip.set('option', 'to', 'syn')

    assert chip.run()

    assert chip.find_result('vg', step='syn') is not None

    # If ['option', 'entrypoint'] didn't work, this test would just build
    # heartbeat, and the design would have half as many cells post-synthesis.
    assert chip.get('metric', 'cells', step='syn', index='0') == 52


def test_entrypoint_via_top():
    chip = siliconcompiler.Chip('heartbeat')

    assert chip.top() == 'heartbeat'

    chip.set('option', 'entrypoint', 'test', step='syn')
    assert chip.top() == 'heartbeat'
    assert chip.top(step='syn') == 'test'
    assert chip.top(step='syn', index='0') == 'test'

    chip.set('option', 'entrypoint', 'test_top')
    assert chip.top() == 'test_top'
    assert chip.top(step='syn') == 'test'
    assert chip.top(step='syn', index='0') == 'test'
