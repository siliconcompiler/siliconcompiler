import copy
import os

import siliconcompiler

import pytest

@pytest.mark.eda
def test_steplist(gcd_chip):
    # Initial run
    gcd_chip.set('option', 'steplist', ['import', 'syn'])
    gcd_chip.run()

    # Make sure we didn't finish
    assert gcd_chip.find_result('gds', step='export') is None
    # Make sure we ran syn
    assert gcd_chip.find_result('vg', step='syn')
    flow = gcd_chip.get('option', 'flow')
    assert gcd_chip.get('flowgraph', flow, 'import', '0', 'status') == siliconcompiler.TaskStatus.SUCCESS
    assert gcd_chip.get('flowgraph', flow, 'syn', '0', 'status') == siliconcompiler.TaskStatus.SUCCESS

    # Re-run
    gcd_chip.set('option', 'steplist', ['syn'])
    gcd_chip.run()
    assert gcd_chip.find_result('gds', step='export') is None
    assert gcd_chip.find_result('vg', step='syn')

    gcd_chip.set('option', 'steplist', ['floorplan'])
    gcd_chip.run()
    assert gcd_chip.find_result('def', step='floorplan')

@pytest.mark.eda
def test_steplist_keep_reports(gcd_chip):
    '''Regression test for making sure that reports from previous steps are
    still mapped when a script is re-run with a steplist.'''
    fresh_chip = siliconcompiler.Chip(gcd_chip.design)
    fresh_chip.schema = gcd_chip.schema.copy()

    # Initial run
    gcd_chip.set('option', 'steplist', ['import', 'syn'])
    gcd_chip.run()
    assert gcd_chip.get('tool', 'yosys', 'report', 'syn', '0', 'cellarea') is not None
    report = gcd_chip.get('tool', 'yosys', 'report', 'syn', '0', 'cellarea')

    # Run a new step from a fresh chip object
    fresh_chip.set('option', 'steplist', ['floorplan'])
    fresh_chip.run()
    assert fresh_chip.get('tool', 'yosys', 'report', 'syn', '0', 'cellarea') == report

@pytest.mark.eda
def test_old_resume(gcd_chip):
    '''Regression test for making sure that using ['option', 'resume'] in a
    previous run does not affect the behavior of a future run when a script is
    re-run with a partial steplist.'''
    # Initial run
    gcd_chip.set('option', 'resume', True)
    gcd_chip.set('option', 'steplist', ['import', 'syn'])
    gcd_chip.run()
    manifest = os.path.join(gcd_chip._getworkdir(step='syn', index='0'), 'outputs', 'gcd.pkg.json')
    mtime_before = os.path.getmtime(manifest)

    # Run a new step from a fresh chip object
    gcd_chip.set('option', 'resume', False)
    gcd_chip.set('option', 'steplist', ['syn'])
    gcd_chip.run()
    mtime_after = os.path.getmtime(manifest)

    assert mtime_after > mtime_before

@pytest.mark.eda
def test_invalid(gcd_chip):
    # Invalid steplist, need to run import first
    gcd_chip.set('option', 'steplist', 'syn')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        # Should be caught by check_manifest()
        gcd_chip.run()

@pytest.mark.eda
def test_invalid_jobinput(gcd_chip):
    gcd_chip.set('option', 'jobname', 'job1')
    gcd_chip.set('option', 'jobinput', 'syn', '0', 'job0')
    gcd_chip.set('option', 'steplist', 'syn')
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()
