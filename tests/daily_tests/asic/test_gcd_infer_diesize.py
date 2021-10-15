import os
import siliconcompiler

import pytest

if __name__ != '__main__':
    from tests.fixtures import test_wrapper

##################################
@pytest.mark.skip(reason="Issue #607")
def test_gcd_infer_diesize():
    '''Test inferring diesize from density/aspectratio/margin arguments

    For now just tests that these flags don't break anything. TODO: is there a
    good way to test that the actual final floorplan is correct?
    '''

    chip = siliconcompiler.Chip()

    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/daily_tests/asic')] + '/examples/gcd/'

    chip.set('design', 'gcd', clobber=True)
    chip.target('asicflow_freepdk45')
    chip.set('asic', 'density', 10)
    chip.set('asic', 'aspectratio', 1)
    chip.set('asic', 'coremargin', 26.6)
    chip.add('source', gcd_ex_dir + 'gcd.v')
    chip.add('constraint', gcd_ex_dir + 'gcd.sdc')
    chip.set('quiet', 'true', clobber=True)
    chip.set('relax', 'true', clobber=True)

    chip.run()

    assert chip.find_result('gds', step='export') is not None

if __name__ == '__main__':
    test_gcd_infer_diesize()
