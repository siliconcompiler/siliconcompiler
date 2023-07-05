import os
import subprocess

import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py(setup_example_test):
    setup_example_test('heartbeat')

    import heartbeat
    heartbeat.main()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_sim(setup_example_test):
    setup_example_test('heartbeat')

    import heartbeat_sim
    heartbeat_sim.main()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_cli(setup_example_test):
    heartbeat_dir = setup_example_test('heartbeat')

    proc = subprocess.run(['bash', os.path.join(heartbeat_dir, 'run.sh')])
    assert proc.returncode == 0


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_parallel(setup_example_test):
    setup_example_test('heartbeat')

    import parallel
    parallel.main()
