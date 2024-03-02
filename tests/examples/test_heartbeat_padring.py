import os
import pytest


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_heartbeat_padring_without_floorplan():
    from heartbeat_padring.build import build_core, build_top

    # Run the build, and verify its outputs.
    core = build_core()
    build_top(core)
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat_top/job0/export/0/outputs/heartbeat_top.gds')
