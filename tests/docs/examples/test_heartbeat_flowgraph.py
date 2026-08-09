import os.path


def test_py(setup_docs_test, has_graphviz):
    # The example defines the flow at module level; writing the image is guarded
    # behind __main__ so that importing it (as the docs build does, to render the
    # graph) does not litter the source tree. Drive the write explicitly here.
    import heartbeat_flowgraph

    assert not os.path.isfile('heartbeat_flowgraph.svg'), \
        "importing the example must not write an image"

    heartbeat_flowgraph.flow.write_flowgraph('heartbeat_flowgraph.svg')

    assert os.path.isfile('heartbeat_flowgraph.svg')
