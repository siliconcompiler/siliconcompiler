import os
import subprocess

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_py(setup_example_test):
    setup_example_test('blinky')

    import blinky
    blinky.main()

    assert os.path.isfile('build/blinky/job0/apr/0/outputs/blinky.asc')


@pytest.mark.eda
@pytest.mark.quick
def test_cli(setup_example_test):
    ex_dir = setup_example_test('blinky')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run.sh')])

    assert proc.returncode == 0
    assert os.path.isfile('build/blinky/job0/apr/0/outputs/blinky.asc')
