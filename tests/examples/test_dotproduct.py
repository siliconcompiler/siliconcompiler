import os
import pytest


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_py_dotproduct():
    from dotproduct import dotproduct
    dotproduct.main()

    assert os.path.isfile(
        'build/mkDotProduct_nt_Int32/job0/write.gds/0/outputs/mkDotProduct_nt_Int32.gds')
