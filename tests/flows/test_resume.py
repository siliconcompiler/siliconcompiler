import siliconcompiler

import pytest
import os

@pytest.mark.eda
def test_resume(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'variable', 'place', '0', 'place_density', 'asdf')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None
    assert gcd_chip.find_result('gds', step='export') is None

    # Fix place step and re-run
    gcd_chip.set('tool', 'openroad', 'variable', 'place', '0', 'place_density', '0.15')
    gcd_chip.set('resume', True)
    gcd_chip.run()

    # Ensure floorplan did not get re-run
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) == old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is not None
    assert gcd_chip.find_result('gds', step='export') is not None
