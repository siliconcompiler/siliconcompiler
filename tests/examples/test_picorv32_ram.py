import os
import pytest


# Run as a daily test, because this takes a long time to build.
@pytest.mark.eda
@pytest.mark.timeout(900)
@pytest.mark.skip(reason='Long runtime, can still timeout at 900s')
def test_picorv32_sram():
    from picorv32_ram import picorv32_ram
    chip = picorv32_ram.build_top()
    chip.run()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/picorv32_top/job0/export/0/outputs/picorv32_top.gds')
