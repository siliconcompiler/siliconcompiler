import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py():
    from fibone import fibone
    fibone.main()

    assert os.path.isfile('build/mkFibOne/job0/export/0/outputs/mkFibOne.gds')
