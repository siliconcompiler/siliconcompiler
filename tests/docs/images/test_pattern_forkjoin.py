import tests.docs.images.image as image

import pytest


@pytest.mark.quick
def test_py(setup_docs_test):
    import pattern_forkjoin  # noqa: F401

    image.compare(pattern_forkjoin, 'pattern_forkjoin.png')
