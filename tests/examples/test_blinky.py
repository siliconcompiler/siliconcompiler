import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_blinky():
    from blinky import blinky
    blinky.main()

    assert os.path.isfile('build/blinky/job0/apr/0/outputs/blinky.asc')
