import os
import filecmp

import pytest


@pytest.mark.quick
def test_py():
    import challenge_nda  # noqa: F401

    test_img = os.path.join('..', '_images', 'siliconcompiler_proxy.png')
    assert os.path.isfile(test_img)
    base_img = os.path.join(os.path.dirname(challenge_nda.__file__), test_img)
    assert filecmp.cmp(test_img, base_img)
