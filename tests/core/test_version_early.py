import siliconcompiler
from siliconcompiler.tools.surelog import parse

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_version_early(capfd):
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', 'fake.v')
    chip.load_target('freepdk45_demo')
    chip.set('option', 'mode', 'asic')
    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', parse)
    chip.set('tool', 'surelog', 'version', '==100.0')

    with pytest.raises(SystemExit):
        chip.run()
    # Fail if any task is run
    out, _ = capfd.readouterr()
    assert "Version check failed" in out
    assert "Finished task in" not in out
