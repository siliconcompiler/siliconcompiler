import os.path


def test_py(setup_docs_test):
    import heartbeat_flowgraph  # noqa: F401

    assert os.path.isfile('heartbeat_flowgraph.svg')
