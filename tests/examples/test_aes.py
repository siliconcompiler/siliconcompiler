import pytest
import os


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_example():
    from aes import aes
    aes.rtl2gds()

    syn_verilog = 'build/aes/job0/syn/0/outputs/aes.vg'
    assert os.path.isfile(syn_verilog)
