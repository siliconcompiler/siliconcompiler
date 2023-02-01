import os
import sys

import pytest

# TODO: Daily test? It takes a minute or ten to build.
@pytest.mark.eda
def test_picorv32_sram(setup_example_test):
    setup_example_test('picorv32_ram')

    import picorv32_ram
    picorv32_ram.build_top()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/picorv32_top/job0/export/0/outputs/picorv32_top.gds')
