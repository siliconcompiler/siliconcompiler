import siliconcompiler
import os
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_yosys_lec(datadir):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    chip.set('option', 'mode', 'asic')

    flow = 'lec'
    chip.node(flow, 'import', 'nop')
    chip.node(flow, 'lec', 'yosys')
    chip.edge(flow, 'import', 'lec')
    chip.set('option', 'flow', flow)

    chip.add('input', 'rtl', 'verilog', os.path.join(lec_dir, 'foo.v'))
    chip.add('input', 'netlist', 'verilog', os.path.join(lec_dir, 'foo.vg'))

    chip.run()

    errors = chip.get('metric', 'lec', '0', 'drvs')

    assert errors == 0

@pytest.mark.eda
@pytest.mark.quick
def test_yosys_lec_broken(datadir):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    chip.set('option', 'mode', 'asic')

    flow = 'lec'
    chip.node(flow, 'import', 'nop')
    chip.node(flow, 'lec', 'yosys')
    chip.edge(flow, 'import', 'lec')
    chip.set('option','flow', flow)

    chip.add('input', 'rtl', 'verilog', os.path.join(lec_dir, 'foo_broken.v'))
    chip.add('input', 'netlist', 'verilog', os.path.join(lec_dir, 'foo_broken.vg'))

    chip.run()

    errors = chip.get('metric', 'lec', '0', 'drvs')

    assert errors == 2

if __name__ == "__main__":
    from tests.fixtures import datadir
    test_yosys_lec(datadir(__file__))
