import os
import pytest

##################################
@pytest.mark.eda
@pytest.mark.quick
def test_gcd_local_py(gcd_chip):
    '''Basic Python API test: build the GCD example using only Python code.
    '''

    gcd_chip.run()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

if __name__ == "__main__":
    from tests.fixtures import gcd_chip
    test_gcd_local_py(gcd_chip())
