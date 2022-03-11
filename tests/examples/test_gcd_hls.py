import siliconcompiler

import os

import pytest

@pytest.fixture
def ex_dir(scroot, monkeypatch):
    ex_dir = os.path.join(scroot, 'examples', 'gcd_hls')

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
    import gcd_hls
    gcd_hls.main()

    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
