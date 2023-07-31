import os
import filecmp

import pytest


@pytest.mark.quick
def test_py():
    import pattern_pipeline  # noqa: F401

    test_img = os.path.join('..', '_images', 'pattern_pipeline.png')
    assert os.path.isfile(test_img)
    base_img = os.path.join(os.path.dirname(pattern_pipeline.__file__), test_img)
    assert filecmp.cmp(test_img, base_img)
