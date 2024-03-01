import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py():
    from heartbeat import heartbeat
    heartbeat.main()

    assert os.path.exists('build/heartbeat/job0/export/0/outputs/heartbeat.gds')


@pytest.mark.eda
@pytest.mark.quick
def test_sim():
    from heartbeat import heartbeat_sim
    heartbeat_sim.main()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_cli(examples_root, run_cli):
    run_cli(os.path.join(examples_root, 'heartbeat', 'run.sh'),
            'build/heartbeat/job0/export/0/outputs/heartbeat.gds')


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_parallel_all_serial():
    from heartbeat import parallel
    parallel.all_serial()


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_parallel_steps():
    from heartbeat import parallel
    parallel.parallel_steps()


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_parallel_flows():
    from heartbeat import parallel
    parallel.parallel_flows()
