import os
import subprocess

import siliconcompiler

import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_py(scroot, monkeypatch):
    ex_dir = os.path.join(scroot, 'examples', 'blinky')

    def _mock_show(chip, filename=None):
        pass

    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(ex_dir)
    # Add test dir to SCPATH to ensure relative paths resolve.
    monkeypatch.setenv('SCPATH', ex_dir, prepend=os.pathsep)
    # Mock chip.show() so it doesn't run.
    monkeypatch.setattr(siliconcompiler.Chip, 'show', _mock_show)

    import blinky
    blinky.main()
    assert os.path.isfile('build/blinky/job0/bitstream/0/outputs/blinky.bit')

@pytest.mark.eda
@pytest.mark.quick
def test_cli(scroot, monkeypatch):
    ex_dir = os.path.join(scroot, 'examples', 'blinky')

    # Add test dir to SCPATH to ensure relative paths resolve.
    monkeypatch.setenv('SCPATH', ex_dir, prepend=os.pathsep)

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run.sh')])

    assert proc.returncode == 0
    assert os.path.isfile('build/blinky/job0/bitstream/0/outputs/blinky.bit')
