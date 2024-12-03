import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py_build():
    from ghdl_fsynopsys import build
    build.main()

    outfile = 'build/binary_4_bit_adder_top/job0/write.gds/0/outputs/binary_4_bit_adder_top.gds'

    assert os.path.isfile(outfile)
