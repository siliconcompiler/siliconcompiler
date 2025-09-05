import pytest
import shutil

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(300)
def test_py_heartbeat():
    from heartbeat import heartbeat
    heartbeat.main()

    assert os.path.exists('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds')


def test_py_make_check():
    from heartbeat import make
    make.check()


def test_py_make_lint():
    from heartbeat import make
    make.lint()

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.parametrize("pdk", ("freepdk45", "asap7"))
def test_py_make_syn(pdk):
    from heartbeat import make
    make.syn(pdk=pdk)

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(300)
@pytest.mark.parametrize("pdk", ("freepdk45", "asap7"))
def test_py_make_asic(pdk):
    from heartbeat import make
    make.asic(pdk=pdk)

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')
    assert os.path.exists('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_py_make_sim_icarus():
    from heartbeat import make
    make.sim(tool="icarus")

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')
    assert os.path.isfile('build/heartbeat/job0/simulate/0/reports/heartbeat_tb.vcd')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_py_make_sim_verilator():
    from heartbeat import make
    make.sim()

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("vivado") is None, reason="Vivado is not available in CI")
def test_py_make_fpga():
    from heartbeat import make
    make.make()

    assert os.path.isfile('build/heartbeat/job0/bitstream/0/outputs/heartbeat.bit')
