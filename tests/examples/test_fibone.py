import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py_fibone():
    from fibone import fibone
    fibone.main()

    assert os.path.isfile('build/fibone/job0/write.gds/0/outputs/mkFibOne.gds')
