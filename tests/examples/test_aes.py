import pytest
import os


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_example():
    from aes import aes
    aes.rtl2gds()

    gds = 'build/aes/job0/write_gds/0/outputs/aes.gds'
    assert os.path.isfile(gds)
