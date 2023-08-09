import os
import pytest


@pytest.mark.quick
def test_py(setup_docs_test):
    import challenge_nda  # noqa: F401

    assert os.path.isfile(os.path.join('..', '_images', 'siliconcompiler_proxy.png'))
