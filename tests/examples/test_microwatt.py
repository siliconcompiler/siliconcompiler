import pytest


# Only run daily -- this will probably be slowish if we make microwatt example
# go from end-to-end, and we already have a quick GHDL test.
@pytest.mark.eda
@pytest.mark.skip(reason='Slow (takes half hour to run)')
def test_py():
    from examples.microwatt import build
    build.main()
