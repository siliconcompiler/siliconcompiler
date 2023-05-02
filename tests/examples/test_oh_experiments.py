import pytest


# Only run daily -- these are kinda slow
@pytest.mark.eda
def test_adder_sweep(setup_example_test, oh_dir):
    setup_example_test('oh_experiments')

    import adder_sweep
    adder_sweep.main()


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_check_area(setup_example_test, oh_dir):
    setup_example_test('oh_experiments')

    import check_area
    check_area.main(5)


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_feedback_loop(setup_example_test, oh_dir):
    setup_example_test('oh_experiments')

    import feedback_loop
    feedback_loop.main(3)
