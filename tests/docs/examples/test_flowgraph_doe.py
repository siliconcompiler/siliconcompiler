import os


def test_py(setup_docs_test, has_graphviz):
    import flowgraph_doe  # noqa: F401

    assert os.path.isfile('flowgraph_doe.svg')
    assert os.path.isfile('doe.json')
