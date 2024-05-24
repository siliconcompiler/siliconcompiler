import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_py():
    from blinky import blinky
    blinky.main()
    assert os.path.isfile('build/blinky/job0/apr/0/outputs/blinky.asc')
