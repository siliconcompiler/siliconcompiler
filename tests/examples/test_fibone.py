import os

import pytest

# No CLI test due to sc-show

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason='schema_rearchitect')
def test_py(setup_example_test):
    setup_example_test('fibone')

    import fibone
    fibone.main()

    assert os.path.isfile('build/mkFibOne/job0/export/0/outputs/mkFibOne.gds')
