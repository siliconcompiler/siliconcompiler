import os
import filecmp

import pytest


@pytest.mark.quick
def test_py():
    import pattern_general  # noqa: F401

    test_img = os.path.join('..', '_images', 'pattern_general.png')
    assert os.path.isfile(test_img)
    base_img = os.path.join(os.path.dirname(pattern_general.__file__), test_img)
    assert filecmp.cmp(test_img, base_img)
