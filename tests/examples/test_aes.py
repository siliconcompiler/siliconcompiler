import pytest
import os


@pytest.mark.eda
@pytest.mark.timeout(1200)
def test_py_aes():
    from aes import aes
    aes.rtl2gds()

    gds = 'build/aes/job0/write.gds/0/outputs/aes.gds'
    assert os.path.isfile(gds)
