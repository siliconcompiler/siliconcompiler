import siliconcompiler
import os
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_yosys_lec(datadir):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip()

    chip.set('arg', 'step', 'lec')
    chip.set('design', 'foo')
    chip.set('mode', 'asic')
    chip.target('yosys_freepdk45')

    chip.add('source', os.path.join(lec_dir, 'foo.v'))
    chip.add('read', 'netlist', 'lec', '0', os.path.join(lec_dir, 'foo.vg'))

    chip.run()

    errors = chip.get('metric', 'lec', '0', 'errors', 'real')

    assert errors == 0

@pytest.mark.eda
@pytest.mark.quick
def test_yosys_lec_broken(datadir):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip()

    chip.set('arg', 'step', 'lec')
    chip.set('design', 'foo')
    chip.set('mode', 'asic')
    chip.target('yosys_freepdk45')

    chip.add('source', os.path.join(lec_dir, 'foo_broken.v'))
    chip.add('read', 'netlist', 'lec', '0', os.path.join(lec_dir, 'foo_broken.vg'))

    chip.run()

    errors = chip.get('metric', 'lec', '0', 'errors', 'real')

    assert errors == 2

if __name__ == "__main__":
    from tests.fixtures import datadir
    test_yosys_lec(datadir(__file__))
