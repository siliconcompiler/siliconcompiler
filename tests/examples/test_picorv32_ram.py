import os
import sys

import pytest

# Run as a daily test, because this takes a long time to build.
@pytest.mark.skip(reason="Not passing routing in OpenROAD.")
@pytest.mark.eda
def test_picorv32_sram(setup_example_test):
    setup_example_test('picorv32_ram')

    import picorv32_ram
    picorv32_ram.build_top()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/picorv32_top/job0/export/0/outputs/picorv32_top.gds')
