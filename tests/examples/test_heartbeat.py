import os
import subprocess
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py():
    from examples.heartbeat import heartbeat
    heartbeat.main()


@pytest.mark.eda
@pytest.mark.quick
def test_sim():
    from examples.heartbeat import heartbeat_sim
    heartbeat_sim.main()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_cli(examples_root):
    proc = subprocess.run(['bash', os.path.join(examples_root, 'heartbeat', 'run.sh')])
    assert proc.returncode == 0


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_parallel_all_serial():
    from examples.heartbeat import parallel
    parallel.all_serial()


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_parallel_steps():
    from examples.heartbeat import parallel
    parallel.parallel_steps()


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_parallel_flows():
    from examples.heartbeat import parallel
    parallel.parallel_flows()
