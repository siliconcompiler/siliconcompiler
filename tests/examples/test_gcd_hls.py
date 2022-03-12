import siliconcompiler

import os

import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_py(setup_example_test):
    setup_example_test('gcd_hls')

    import gcd_hls
    gcd_hls.main()

    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
