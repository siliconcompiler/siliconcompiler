import pytest

@pytest.mark.eda
def test_timeout(gcd_chip):
    # 0 seconds guarantees a timeout
    gcd_chip.set('flowgraph', 'asicflow', 'import', '0', 'timeout', 0)

    # Expect that command exits early
    # TODO: automated check that run timed out vs failed for a different reason
    with pytest.raises(SystemExit):
        gcd_chip.run()
