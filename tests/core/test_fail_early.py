import siliconcompiler
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.surelog import parse
from siliconcompiler._common import SiliconCompilerError
import pytest
import os
from siliconcompiler.targets import freepdk45_demo


def test_fail_early(capfd):
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', 'fake.v')
    chip.use(freepdk45_demo)
    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', parse)
    chip.node(flow, 'syn', syn_asic)
    chip.edge(flow, 'import', 'syn')

    try:
        chip.run(raise_exception=True)
    except SiliconCompilerError:
        # Fail if 'syn' step is run
        out, _ = capfd.readouterr()
        assert "Halting step 'syn'" not in out


@pytest.mark.eda
@pytest.mark.quick
def test_tool_failure_manifest(datadir):
    chip = siliconcompiler.Chip('gcd')
    chip.set('input', 'rtl', 'verilog', f'{datadir}/gcd_bad_inst.v')
    chip.use(freepdk45_demo)
    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', parse)
    chip.node(flow, 'syn', syn_asic)
    chip.edge(flow, 'import', 'syn')

    with pytest.raises(SiliconCompilerError):
        assert chip.run()

    cfg = f'{chip.getworkdir(step="syn", index="0")}/outputs/gcd.pkg.json'
    assert os.path.exists(cfg)
