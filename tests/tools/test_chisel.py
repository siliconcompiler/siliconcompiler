import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
# @pytest.skip(reason='Scala not installed on test runner')
def test_chisel(datadir):
    design = 'gcd'
    gcd_src = os.path.join(datadir, f'{design}.scala')
    step = 'import'

    chip = siliconcompiler.Chip(loglevel="INFO")

    chip.add('source', gcd_src)
    chip.set('design', design)
    chip.set('mode', 'sim')
    chip.set('arg', 'step', step)
    chip.target('chisel')

    chip.run()

    assert chip.find_result('v', step=step) is not None
