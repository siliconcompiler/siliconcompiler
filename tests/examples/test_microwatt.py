import pytest
import os


# Only run daily -- this will probably be slowish if we make microwatt example
# go from end-to-end, and we already have a quick GHDL test.
@pytest.mark.eda
@pytest.mark.timeout(2400)
def test_py():
    from microwatt import build
    build.main()

    verilog = 'build/aes/job0/syn/0/outputs/soc.vg'
    assert os.path.isfile(verilog)
