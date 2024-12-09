import pytest
import siliconcompiler


@pytest.mark.eda
def test_timeout(gcd_chip):
    # 0 seconds guarantees a timeout
    gcd_chip.set('option', 'timeout', 0, step='import.verilog', index='0')

    # Expect that command exits early
    # TODO: automated check that run timed out vs failed for a different reason
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()
