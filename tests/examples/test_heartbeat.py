import os
import subprocess

import pytest

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason='schema_rearchitect')
def test_py(setup_example_test):
    setup_example_test('heartbeat')

    import heartbeat
    heartbeat.main()

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason='schema_rearchitect')
def test_cli(setup_example_test):
    heartbeat_dir = setup_example_test('heartbeat')

    proc = subprocess.run(['bash', os.path.join(heartbeat_dir, 'run.sh')])
    assert proc.returncode == 0

@pytest.mark.eda
@pytest.mark.skip(reason='schema_rearchitect')
def test_parallel(setup_example_test):
    setup_example_test('heartbeat')

    import parallel
    parallel.main()
