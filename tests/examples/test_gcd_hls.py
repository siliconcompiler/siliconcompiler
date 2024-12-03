import os
import pytest


@pytest.mark.eda
@pytest.mark.timeout(1200)
def test_py_gcd_hls():
    from gcd_hls import gcd_hls
    gcd_hls.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')
