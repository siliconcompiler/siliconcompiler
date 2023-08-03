import tests.docs.images.image as image

import pytest


@pytest.mark.quick
def test_py(setup_docs_test):
    import challenge_nda  # noqa: F401

    image.compare(challenge_nda, 'siliconcompiler_proxy.png')
