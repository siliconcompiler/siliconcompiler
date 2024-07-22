import os

import pytest

import siliconcompiler
from siliconcompiler.flows import lintflow


@pytest.mark.quick
@pytest.mark.eda
@pytest.mark.parametrize('tool', ('verilator', 'slang'))
def test_lintflow(scroot, tool):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.input(v_src)

    chip.use(lintflow, tool=tool)
    chip.set('option', 'flow', 'lintflow')

    chip.run()
