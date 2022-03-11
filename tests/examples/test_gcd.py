import siliconcompiler

import os
import subprocess

import pytest

@pytest.fixture
def ex_dir(scroot, monkeypatch):
    ex_dir = os.path.join(scroot, 'examples', 'gcd')

    def _mock_show(chip, filename=None, extra_options=None):
        pass

    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(ex_dir)
    # Add test dir to SCPATH to ensure relative paths resolve.
    monkeypatch.setenv('SCPATH', ex_dir, prepend=os.pathsep)
    # Mock chip.show() so it doesn't run.
    monkeypatch.setattr(siliconcompiler.Chip, 'show', _mock_show)

    return ex_dir

@pytest.mark.eda
@pytest.mark.quick
def test_py(ex_dir):
    import gcd
    gcd.main()
    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
    # Verify that report file was generated.
    assert os.path.isfile('build/gcd/job0/report.html')

@pytest.mark.eda
@pytest.mark.quick
def test_cli(ex_dir):
    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run.sh')])
    assert proc.returncode == 0

@pytest.mark.eda
@pytest.mark.quick
def test_py_sky130(ex_dir):
    import gcd_skywater
    gcd_skywater.main()

    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

    manifest = 'build/gcd/signoff/signoff/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    chip = siliconcompiler.Chip()
    chip.read_manifest(manifest)

    # Verify that the build was LVS and DRC clean.
    assert chip.get('metric', 'lvs', '0', 'errors', 'real') == 0
    assert chip.get('metric', 'drc', '0', 'errors', 'real') == 0

@pytest.mark.eda
def test_cli_asap7(ex_dir):
    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run_asap7.sh')])
    assert proc.returncode == 0
