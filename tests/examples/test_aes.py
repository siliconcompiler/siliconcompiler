import pytest

import os.path


@pytest.mark.eda
@pytest.mark.ready
@pytest.mark.nocpulimit
@pytest.mark.timeout(1800)
def test_py_aes():
    from aes import aes
    aes.main()

    assert os.path.isfile('build/aes/job0/write.gds/0/outputs/aes.gds')
