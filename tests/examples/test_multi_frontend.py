import os
import pytest


# Run as a daily test, because this takes a long time to build.
@pytest.mark.eda
@pytest.mark.timeout(900)
def test_multiple_frontends():
    from multi_frontend import multi_frontend
    multi_frontend.main()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/top/job0/write_gds/0/outputs/top.gds')
