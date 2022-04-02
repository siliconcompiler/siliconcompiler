import os
import pytest
import siliconcompiler
import sys

@pytest.mark.eda
def test_heartbeat_padring_with_floorplan():
    # Use an empty chip object to quickly get sc root dir.
    chip = siliconcompiler.Chip()
    ex_dir = f'{chip.scroot}/../examples/heartbeat_padring'

    # Import build script methods from the example dir.
    sys.path.append(ex_dir)
    from floorplan_build import build_core, build_top

    # Run the build, and verify its outputs.
    os.chdir(ex_dir)
    build_core()
    build_top()
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat_top/job0/export/0/outputs/heartbeat_top.gds')

@pytest.mark.eda
def test_heartbeat_padring_without_floorplan():
    # Use an empty chip object to quickly get sc root dir.
    chip = siliconcompiler.Chip()
    ex_dir = f'{chip.scroot}/../examples/heartbeat_padring'

    # Import build script methods from the example dir.
    sys.path.append(ex_dir)
    from build import build_core, build_top

    # Run the build, and verify its outputs.
    os.chdir(ex_dir)
    build_core()
    build_top()
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat_top/job0/export/0/outputs/heartbeat_top.gds')
