import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_sim_icarus_no_trace():
    from adder_cocotb import make
    make.sim_icarus(trace=False)

    assert os.path.isfile('build/adder/job0/adder.pkg.json')
    assert not os.path.isfile('build/adder/job0/simulate/0/reports/adder.vcd')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_sim_icarus_vcd():
    from adder_cocotb import make
    make.sim_icarus(trace=True)

    assert os.path.isfile('build/adder/job0/adder.pkg.json')
    assert os.path.isfile('build/adder/job0/simulate/0/reports/adder.vcd')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_sim_verilator_no_trace():
    from adder_cocotb import make
    make.sim_verilator(trace=False, trace_type="vcd")

    assert os.path.isfile('build/adder/job0/adder.pkg.json')
    assert not os.path.isfile('build/adder/job0/simulate/0/reports/adder.vcd')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_sim_verilator_vcd():
    from adder_cocotb import make
    make.sim_verilator(trace=True, trace_type="vcd")

    assert os.path.isfile('build/adder/job0/adder.pkg.json')
    assert os.path.isfile('build/adder/job0/simulate/0/reports/adder.vcd')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_sim_verilator_fst():
    from adder_cocotb import make
    make.sim_verilator(trace=True, trace_type="fst")

    assert os.path.isfile('build/adder/job0/adder.pkg.json')
    assert os.path.isfile('build/adder/job0/simulate/0/reports/adder.fst')
