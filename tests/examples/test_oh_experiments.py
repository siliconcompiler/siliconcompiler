import pytest

import os.path


# Only run daily -- these are kinda slow
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(300)
def test_py_adder_sweep():
    from oh_experiments import adder_sweep
    adder_sweep.main()

    assert os.path.isfile('build/oh_add/N8/oh_add.pkg.json')
    assert os.path.isfile('build/oh_add/N16/oh_add.pkg.json')
    assert os.path.isfile('build/oh_add/N32/oh_add.pkg.json')
    assert os.path.isfile('build/oh_add/N64/oh_add.pkg.json')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(300)
def test_py_check_area():
    from oh_experiments import check_area
    check_area.main(5)

    assert os.path.isfile('build/oh/job0/rtl.asic_and2.pkg.json')
    assert os.path.isfile('build/oh/job0/rtl.asic_and3.pkg.json')
    assert os.path.isfile('build/oh/job0/rtl.asic_and4.pkg.json')
    assert os.path.isfile('build/oh/job0/rtl.asic_ao21.pkg.json')
    assert os.path.isfile('build/oh/job0/rtl.asic_ao211.pkg.json')
