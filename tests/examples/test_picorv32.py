import os
import pytest


# Run as a daily test, because this takes a long time to build.
@pytest.mark.eda
@pytest.mark.timeout(900)
@pytest.mark.skip(reason='Long runtime, can still timeout at 900s')
def test_picorv32():
    from examples.picorv32 import picorv32
    picorv32.rtl2gds()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/picorv32/job0/export/0/outputs/picorv32.gds')
