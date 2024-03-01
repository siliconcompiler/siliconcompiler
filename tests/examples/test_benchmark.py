import siliconcompiler
import pytest


def test_scalability_serial():
    from examples.benchmark import scalability
    scalability.run_long_serial(5, 5)


def test_scalability_parallel():
    from examples.benchmark import scalability
    scalability.run_wide_parallel(5)


@pytest.mark.eda
@pytest.mark.timeout(600)
@pytest.mark.skip(reason='This test takes a long time on small machines')
def test_benchmark(monkeypatch):
    org_init = siliconcompiler.Chip.__init__

    def _mock_init(chip, design, loglevel=None):
        org_init(chip, design, loglevel=loglevel)

        chip.set('option', 'to', 'syn')

    monkeypatch.setattr(siliconcompiler.Chip, '__init__', _mock_init)

    from examples.benchmark import benchmark
    benchmark.main()
