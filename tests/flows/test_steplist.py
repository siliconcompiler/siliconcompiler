import siliconcompiler

import pytest

@pytest.mark.eda
def test_steplist(gcd_chip):
    # Initial run
    gcd_chip.set('steplist', ['import', 'syn'])
    gcd_chip.run()

    # Make sure we didn't finish
    assert gcd_chip.find_result('gds', step='export') is None
    # Make sure we ran syn
    assert gcd_chip.find_result('vg', step='syn')
    assert gcd_chip.get('flowstatus', 'import', '0', 'status') == siliconcompiler.TaskStatus.SUCCESS
    assert gcd_chip.get('flowstatus', 'syn', '0', 'status') == siliconcompiler.TaskStatus.SUCCESS

    # Re-run
    gcd_chip.set('steplist', ['syn'])
    gcd_chip.run()
    assert gcd_chip.find_result('gds', step='export') is None
    assert gcd_chip.find_result('vg', step='syn')

    gcd_chip.set('steplist', ['floorplan'])
    gcd_chip.run()
    assert gcd_chip.find_result('def', step='floorplan')

@pytest.mark.eda
def test_invalid(gcd_chip):
    # Invalid steplist, need to run import first
    gcd_chip.set('steplist', 'syn')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        # Should be caught by check_manifest()
        gcd_chip.run()

@pytest.mark.eda
def test_invalid_jobinput(gcd_chip):
    gcd_chip.set('jobname', 'job1')
    gcd_chip.set('jobinput', 'job1', 'syn', '0', 'job0')
    gcd_chip.set('steplist', 'syn')
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()
