import os
import pytest


# Run as a daily test, because this takes a long time to build.
@pytest.mark.eda
@pytest.mark.timeout(2400)
def test_py_picorv32():
    from picorv32 import picorv32
    picorv32.rtl2gds()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/picorv32/job0/write.gds/0/outputs/picorv32.gds')
