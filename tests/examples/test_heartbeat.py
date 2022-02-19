import os
import subprocess

import siliconcompiler

import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_heartbeat_py(scroot, monkeypatch):
    heartbeat_dir = os.path.join(scroot, 'examples', 'heartbeat')

    def _mock_show(chip, filename=None):
        pass

    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(heartbeat_dir)
    # Add test dir to SCPATH to ensure relative paths resolve.
    monkeypatch.setenv('SCPATH', heartbeat_dir, prepend=os.pathsep)
    # Mock chip.show() so it doesn't run.
    monkeypatch.setattr(siliconcompiler.Chip, 'show', _mock_show)

    import heartbeat
    heartbeat.main()

@pytest.mark.eda
@pytest.mark.quick
def test_heartbeat_cli(scroot, monkeypatch):
    heartbeat_dir = os.path.join(scroot, 'examples', 'heartbeat')

    # Add test dir to SCPATH to ensure relative paths resolve.
    monkeypatch.setenv('SCPATH', heartbeat_dir, prepend=os.pathsep)

    proc = subprocess.run(['bash', os.path.join(heartbeat_dir, 'run.sh')])

    assert proc.returncode == 0
