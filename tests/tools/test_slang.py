import os
import pytest

import siliconcompiler
from siliconcompiler.tools.slang import lint


@pytest.mark.quick
@pytest.mark.eda
def test_lint(scroot):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.input(v_src)

    chip.set('option', 'mode', 'sim')

    flow = 'lint'
    chip.node(flow, 'lint', lint)
    chip.set('option', 'flow', flow)

    chip.run()
