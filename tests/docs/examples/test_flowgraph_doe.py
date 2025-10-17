import os

import pytest


@pytest.mark.timeout(60)
def test_py(setup_docs_test, has_graphviz):
    import flowgraph_doe  # noqa: F401

    assert os.path.isfile('flowgraph_doe.svg')
