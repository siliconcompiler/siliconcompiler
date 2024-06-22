import pytest
import os


# Only run daily -- these are kinda slow
@pytest.mark.eda
def test_adder_sweep():
    from oh_experiments import adder_sweep
    adder_sweep.main()

    assert os.path.isfile('build/oh_add/job0/oh_add.pkg.json')


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_check_area():
    from oh_experiments import check_area
    check_area.main(5)

    assert os.path.isfile('build/asic_ao221/job0/asic_ao221.pkg.json')
    assert os.path.isfile('build/asic_ao32/job0/asic_ao32.pkg.json')
    assert os.path.isfile('build/asic_aoi31/job0/asic_aoi31.pkg.json')
    assert os.path.isfile('build/asic_clkbuf/job0/asic_clkbuf.pkg.json')
    assert os.path.isfile('build/asic_oai21/job0/asic_oai21.pkg.json')


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_feedback_loop():
    from oh_experiments import feedback_loop
    feedback_loop.main(3)

    assert os.path.isfile('build/oh_add/job0/oh_add.pkg.json')
    assert os.path.isfile('build/oh_add/job1/oh_add.pkg.json')
    assert os.path.isfile('build/oh_add/job2/oh_add.pkg.json')
    assert os.path.isfile('build/oh_add/job3/oh_add.pkg.json')
