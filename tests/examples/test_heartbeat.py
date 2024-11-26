import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_heartbeat():
    from heartbeat import heartbeat
    heartbeat.main()

    assert os.path.exists('build/heartbeat/job0/write_gds/0/outputs/heartbeat.gds')


@pytest.mark.eda
@pytest.mark.quick
def test_py_heartbeat_sim():
    from heartbeat import heartbeat_sim
    heartbeat_sim.main()

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')


@pytest.mark.eda
@pytest.mark.quick
def test_py_heartbeat_sim_verilator():
    from heartbeat import heartbeat_sim_verilator
    heartbeat_sim_verilator.main()

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_sh_run(examples_root, run_cli):
    run_cli(os.path.join(examples_root, 'heartbeat', 'run.sh'),
            'build/heartbeat/job0/write_gds/0/outputs/heartbeat.gds')


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_parallel_all_serial():
    from heartbeat import parallel
    parallel.all_serial()

    assert os.path.isdir('build/heartbeat/serial_0_0')
    assert os.path.isdir('build/heartbeat/serial_0_1')
    assert os.path.isdir('build/heartbeat/serial_1_0')
    assert os.path.isdir('build/heartbeat/serial_1_1')


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_parallel_steps():
    from heartbeat import parallel
    parallel.parallel_steps()

    assert os.path.isdir('build/heartbeat/parasteps_0')
    assert os.path.isdir('build/heartbeat/parasteps_1')


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_parallel_flows():
    from heartbeat import parallel
    parallel.parallel_flows()

    assert os.path.isdir('build/heartbeat/paraflows_0')
    assert os.path.isdir('build/heartbeat/paraflows_1')


def test_py_parallel():
    # Dummy test to simplify test checking
    # The parallel examples needs to be split into separate file
    assert True


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skip(reason="Vivado is not available in CI")
def test_py_heartbeat_fpga():
    from heartbeat import heartbeat_fpga
    heartbeat_fpga.main()

    assert os.path.isfile('build/heartbeat/job0/bitstream/0/outputs/heartbeat.bit')
