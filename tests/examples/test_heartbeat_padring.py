import os
import sys

import pytest


@pytest.mark.eda
@pytest.mark.skip(reason='Floorplan module has not been updated for 2023 schema changes')
def test_heartbeat_padring_with_floorplan(setup_example_test):
    setup_example_test('heartbeat_padring')

    from floorplan_build import build_core, build_top

    # Run the build, and verify its outputs.
    core = build_core()
    build_top(core)
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat_top/job0/export/0/outputs/heartbeat_top.gds')


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_heartbeat_padring_without_floorplan(setup_example_test):
    setup_example_test('heartbeat_padring')

    from build import build_core, build_top

    # Run the build, and verify its outputs.
    core = build_core()
    build_top(core)
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat_top/job0/export/0/outputs/heartbeat_top.gds')

    del sys.modules['build']
