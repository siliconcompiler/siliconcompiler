import os
import subprocess

import siliconcompiler

import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_py(setup_example_test):
    setup_example_test('blinky')

    import blinky
    blinky.main()

    assert os.path.isfile('build/blinky/job0/bitstream/0/outputs/blinky.bit')

@pytest.mark.eda
@pytest.mark.quick
def test_cli(setup_example_test):
    ex_dir = setup_example_test('blinky')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run.sh')])

    assert proc.returncode == 0
    assert os.path.isfile('build/blinky/job0/bitstream/0/outputs/blinky.bit')
