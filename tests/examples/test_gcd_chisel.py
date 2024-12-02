import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py_gcd_chisel():
    from gcd_chisel import gcd_chisel
    gcd_chisel.main()

    assert os.path.isfile('build/GCD/job0/write.gds/0/outputs/GCD.gds')
