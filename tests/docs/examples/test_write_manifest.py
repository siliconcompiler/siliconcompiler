import os

import pytest


@pytest.mark.quick
def test_py(setup_docs_test):
    import write_manifest  # noqa: F401

    assert os.path.isfile('hello_world.json')
