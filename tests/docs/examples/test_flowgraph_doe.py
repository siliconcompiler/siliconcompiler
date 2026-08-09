import os

import pytest


@pytest.mark.timeout(60)
def test_py(setup_docs_test, has_graphviz):
    # See test_heartbeat_flowgraph: the write is guarded behind __main__, so the
    # test drives it rather than relying on an import side effect.
    import flowgraph_doe

    assert not os.path.isfile('flowgraph_doe.svg'), \
        "importing the example must not write an image"

    flowgraph_doe.flow.write_flowgraph('flowgraph_doe.svg')

    assert os.path.isfile('flowgraph_doe.svg')
