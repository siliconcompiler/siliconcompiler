import os
import subprocess
import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_py():
    from examples.blinky import blinky
    blinky.main()

    assert os.path.isfile('build/blinky/job0/apr/0/outputs/blinky.asc')


@pytest.mark.eda
@pytest.mark.quick
def test_cli(examples_root):
    proc = subprocess.run(['bash', os.path.join(examples_root, 'blinky', 'run.sh')])

    assert proc.returncode == 0
    assert os.path.isfile('build/blinky/job0/apr/0/outputs/blinky.asc')
