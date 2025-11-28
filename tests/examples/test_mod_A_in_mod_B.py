import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(150)
def test_py_silicon_compiler_mod_A_in_mod_B():
    from mod_A_in_mod_B import silicon_compiler_mod_A_in_mod_B
    silicon_compiler_mod_A_in_mod_B.main()

    assert os.path.exists('build/A/job0/write.gds/0/outputs/A.gds')
    assert os.path.exists('build/B/job0/write.gds/0/outputs/B.gds')
