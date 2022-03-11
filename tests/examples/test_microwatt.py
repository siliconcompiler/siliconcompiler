import os

import siliconcompiler

import pytest

# Only run daily -- this will probably be slowish if we make microwatt example
# go from end-to-end, and we already have a quick GHDL test.

@pytest.mark.eda
def test_py(scroot, monkeypatch, microwatt_dir):
    # Note: value of microwatt_dir is unused, but specifying it is important to
    # ensure that the submodule is cloned.

    ex_dir = os.path.join(scroot, 'examples', 'microwatt')

    def _mock_show(chip, filename=None):
        pass

    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(ex_dir)
    # Add test dir to SCPATH to ensure relative paths resolve.
    monkeypatch.setenv('SCPATH', ex_dir, prepend=os.pathsep)
    # Mock chip.show() so it doesn't run.
    monkeypatch.setattr(siliconcompiler.Chip, 'show', _mock_show)

    import build
    build.main()
