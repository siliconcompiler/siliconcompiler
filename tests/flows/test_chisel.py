import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_chisel(datadir):
    design = 'gcd'
    gcd_src = os.path.join(datadir, f'{design}.scala')

    chip = siliconcompiler.Chip(loglevel="INFO")

    chip.add('source', gcd_src)
    chip.set('design', design)
    chip.set('frontend', 'chisel')
    chip.load_target('freepdk45_demo')

    chip.run()

    assert chip.find_result('gds', step='export') is not None
