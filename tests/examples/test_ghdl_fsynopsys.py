import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py():
    from ghdl_fsynopsys import build
    build.main()

    outfile = 'build/binary_4_bit_adder_top/job0/syn/0/outputs/binary_4_bit_adder_top.vg'

    assert os.path.isfile(outfile)
