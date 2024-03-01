import pytest


# Only run daily -- these are kinda slow
@pytest.mark.eda
def test_adder_sweep():
    from oh_experiments import adder_sweep
    adder_sweep.main()


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_check_area():
    from oh_experiments import check_area
    check_area.main(5)


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_feedback_loop():
    from oh_experiments import feedback_loop
    feedback_loop.main(3)
