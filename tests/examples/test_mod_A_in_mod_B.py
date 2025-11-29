import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(150)
def test_py_silicon_compiler_mod_A_in_mod_B():
    from mod_A_in_mod_B import silicon_compiler_mod_A_in_mod_B
    silicon_compiler_mod_A_in_mod_B.build_top()

    assert os.path.exists('build/and/job0/write.gds/0/outputs/mod_and.gds')
    assert os.path.exists('build/top/job0/write.gds/0/outputs/top.gds')
