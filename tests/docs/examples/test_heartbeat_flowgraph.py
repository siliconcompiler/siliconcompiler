import os

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_py():
    import heartbeat_flowgraph  # noqa: F401

    assert os.path.isfile('heartbeat_flowgraph.svg')
    # check if netlist exists
    assert os.path.isfile('build/heartbeat/job0/syn/0/outputs/heartbeat.vg')
