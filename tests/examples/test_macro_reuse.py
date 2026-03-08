import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_top():
    from macro_reuse import make
    make.build_top()

    assert os.path.exists('build/and/job0/write.gds/0/outputs/mod_and.gds.gz')
    assert os.path.exists('build/top/job0/write.gds/0/outputs/top.gds.gz')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_flat():
    from macro_reuse import make
    make.build_flat()

    assert os.path.exists('build/top/job0/write.gds/0/outputs/top.gds.gz')
