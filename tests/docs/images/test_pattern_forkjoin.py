import os
import filecmp

import pytest


@pytest.mark.quick
def test_py():
    import pattern_forkjoin  # noqa: F401

    test_img = os.path.join('..', '_images', 'pattern_forkjoin.png')
    assert os.path.isfile(test_img)
    base_img = os.path.join(os.path.dirname(pattern_forkjoin.__file__), test_img)
    assert filecmp.cmp(test_img, base_img)
