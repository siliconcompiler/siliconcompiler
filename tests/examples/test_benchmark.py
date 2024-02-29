import siliconcompiler
import pytest


def test_scalability_serial(setup_example_test):
    setup_example_test('benchmark')

    import scalability
    scalability.run_long_serial(5, 5)


def test_scalability_parallel(setup_example_test):
    setup_example_test('benchmark')

    import scalability
    scalability.run_wide_parallel(5)


@pytest.mark.eda
@pytest.mark.timeout(600)
@pytest.mark.skip(reason='This test takes a long time on small machines')
def test_benchmark(setup_example_test, monkeypatch):
    setup_example_test('benchmark')

    org_init = siliconcompiler.Chip.__init__

    def _mock_init(chip, design, loglevel=None):
        org_init(chip, design, loglevel=loglevel)

        chip.set('option', 'to', 'syn')

    monkeypatch.setattr(siliconcompiler.Chip, '__init__', _mock_init)

    import benchmark
    benchmark.main()
