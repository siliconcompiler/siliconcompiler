import tests.docs.images.image as image

import pytest


@pytest.mark.quick
def test_py():
    import challenge_nsquared  # noqa: F401

    image.compare(challenge_nsquared, 'challenge_nsquared.png')
    image.compare(challenge_nsquared, 'siliconcompiler_ir.png')
