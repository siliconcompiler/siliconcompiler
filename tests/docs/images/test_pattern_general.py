import tests.docs.images.image as image

import pytest


@pytest.mark.quick
def test_py(setup_docs_test):
    import pattern_general  # noqa: F401

    image.compare(pattern_general, 'pattern_general.png')
