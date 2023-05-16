import os

import pytest

import siliconcompiler
from siliconcompiler.flows import lintflow
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.verilator import lint


@pytest.mark.quick
@pytest.mark.eda
def test_lintflow(scroot):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.input(v_src)

    chip.use(lintflow)
    chip.set('option', 'flow', 'lintflow')

    chip.run()


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
