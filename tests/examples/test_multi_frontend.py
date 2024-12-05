import os
import pytest


@pytest.mark.eda
@pytest.mark.timeout(1800)
def test_py_multi_frontend():
    from multi_frontend import multi_frontend
    multi_frontend.main()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/top/job0/write.gds/0/outputs/top.gds')
