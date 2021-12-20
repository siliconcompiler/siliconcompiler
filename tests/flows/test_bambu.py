import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_bambu(datadir):
    design = 'gcd'
    gcd_src = os.path.join(datadir, f'{design}.c')

    chip = siliconcompiler.Chip(loglevel="INFO")

    chip.add('source', gcd_src)
    chip.set('design', design)
    chip.set('frontend', 'bambu')
    chip.target('asicflow_freepdk45')

    chip.run()

    assert chip.find_result('gds', step='export') is not None
