import tests.docs.images.image as image

import pytest


@pytest.mark.quick
def test_py():
    import pattern_pipeline  # noqa: F401

    image.compare(pattern_pipeline, 'pattern_pipeline.png')
