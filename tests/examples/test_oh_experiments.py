import os

import siliconcompiler

import pytest

# Only run daily -- these are kinda slow

@pytest.fixture
def setup(scroot, monkeypatch, oh_dir):
    # Note: value of oh_dir is unused, but specifying it is important to
    # ensure that the submodule is cloned.
    ex_dir = os.path.join(scroot, 'examples', 'oh_experiments')

    def _mock_show(chip, filename=None):
        pass

    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(ex_dir)
    # Add test dir to SCPATH to ensure relative paths resolve.
    monkeypatch.setenv('SCPATH', ex_dir, prepend=os.pathsep)
    # Mock chip.show() so it doesn't run.
    monkeypatch.setattr(siliconcompiler.Chip, 'show', _mock_show)

@pytest.mark.eda
def test_adder_sweep(setup):
    import adder_sweep
    adder_sweep.main()

@pytest.mark.eda
def test_check_area(setup):
    import check_area
    check_area.main()

@pytest.mark.eda
def test_feedback_loop(setup):
    import feedback_loop
    feedback_loop.main()
