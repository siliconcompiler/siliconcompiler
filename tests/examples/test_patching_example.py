import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py_patching_example():
    from patching_example import spi
    spi.main()
    
    assert os.path.isfile('build/spi/job0/write.gds/0/outputs/spi.gds')
