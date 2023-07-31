import tests.docs.images.image as image

import pytest


@pytest.mark.quick
def test_py():
    import pattern_general  # noqa: F401

    image.compare(pattern_general, 'pattern_general.png')
