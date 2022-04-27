import os
import pytest
import siliconcompiler
import sys

@pytest.mark.eda
def test_heartbeat_padring_with_floorplan(setup_example_test, oh_dir):
    setup_example_test('heartbeat_padring')

    from floorplan_build import build_core, build_top

    # Run the build, and verify its outputs.
    build_core()
    build_top()
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat_top/job0/export/0/outputs/heartbeat_top.gds')

@pytest.mark.eda
def test_heartbeat_padring_without_floorplan(setup_example_test, oh_dir):
    setup_example_test('heartbeat_padring')

    from build import build_core, build_top

    # Run the build, and verify its outputs.
    build_core()
    build_top()
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat_top/job0/export/0/outputs/heartbeat_top.gds')

    del sys.modules['build']
