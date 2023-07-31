import os
import filecmp

import pytest


@pytest.mark.quick
def test_py():
    import challenge_nsquared  # noqa: F401

    test_img = os.path.join('..', '_images', 'challenge_nsquared.png')
    assert os.path.isfile(test_img)
    base_img = os.path.join(os.path.dirname(challenge_nsquared.__file__), test_img)
    assert filecmp.cmp(test_img, base_img)

    test_img = os.path.join('..', '_images', 'siliconcompiler_ir.png')
    assert os.path.isfile(test_img)
    base_img = os.path.join(os.path.dirname(challenge_nsquared.__file__), test_img)
    assert filecmp.cmp(test_img, base_img)
