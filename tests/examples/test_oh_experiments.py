import pytest

# Only run daily -- these are kinda slow

@pytest.mark.eda
def test_adder_sweep(setup_example_test):
    setup_example_test('oh_experiments')

    import adder_sweep
    adder_sweep.main()

@pytest.mark.eda
def test_check_area(setup_example_test):
    setup_example_test('oh_experiments')

    import check_area
    check_area.main()

@pytest.mark.eda
def test_feedback_loop(setup_example_test):
    setup_example_test('oh_experiments')

    import feedback_loop
    feedback_loop.main()
