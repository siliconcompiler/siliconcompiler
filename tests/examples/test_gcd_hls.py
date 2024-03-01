import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py():
    from gcd_hls import gcd_hls
    gcd_hls.main()

    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
