import os
import pytest


# Run as a daily test, because this takes a long time to build.
@pytest.mark.eda
@pytest.mark.nocpulimit
@pytest.mark.timeout(2100)
def test_py_picorv32_ram():
    from picorv32_ram import picorv32_ram
    chip = picorv32_ram.build_top()
    assert chip.run()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/picorv32_top/job0/write.gds/0/outputs/picorv32_top.gds')
