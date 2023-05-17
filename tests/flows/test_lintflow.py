import os

import pytest

import siliconcompiler
from siliconcompiler.flows import lintflow


@pytest.mark.quick
@pytest.mark.eda
def test_lintflow(scroot):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.input(v_src)

    chip.set('option', 'mode', 'sim')

    chip.use(lintflow)
    chip.set('option', 'flow', 'lintflow')

    chip.run()
