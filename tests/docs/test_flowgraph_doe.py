import os

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_py(setup_docs_test):
    setup_docs_test()

    import flowgraph_doe  # noqa: F401

    assert os.path.isfile('flowgraph_doe.svg')
    assert os.path.isfile('doe.json')
