import pytest
import os


# Only run daily -- these are kinda slow
@pytest.mark.eda
def test_py_adder_sweep():
    from oh_experiments import adder_sweep
    adder_sweep.main()

    assert os.path.isfile('build/oh_add/job0/oh_add.pkg.json')


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_py_check_area():
    from oh_experiments import check_area
    check_area.main(5)

    assert os.path.isfile('build/asic_and2/job0/asic_and2.pkg.json')
    assert os.path.isfile('build/asic_and3/job0/asic_and3.pkg.json')
    assert os.path.isfile('build/asic_and4/job0/asic_and4.pkg.json')
    assert os.path.isfile('build/asic_ao21/job0/asic_ao21.pkg.json')
    assert os.path.isfile('build/asic_ao211/job0/asic_ao211.pkg.json')


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_py_feedback_loop():
    from oh_experiments import feedback_loop
    feedback_loop.main(2)

    assert os.path.isfile('build/oh_add/job0/oh_add.pkg.json')
    assert os.path.isfile('build/oh_add/job1/oh_add.pkg.json')
    assert os.path.isfile('build/oh_add/job2/oh_add.pkg.json')
