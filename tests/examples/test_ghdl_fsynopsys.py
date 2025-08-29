import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(600)
def test_py_build():
    from ghdl_fsynopsys import build
    build.main()

    assert os.path.isfile('build/ghdl_fsynopsys/job0/write.gds/0/outputs/binary_4_bit_adder_top.gds')
