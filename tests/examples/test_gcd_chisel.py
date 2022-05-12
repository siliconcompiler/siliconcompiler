import os

import pytest

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason='schema_rearchitect')
def test_py(setup_example_test):
    setup_example_test('gcd_chisel')

    import gcd_chisel
    gcd_chisel.main()

    assert os.path.isfile('build/GCD/job0/export/0/outputs/GCD.gds')
