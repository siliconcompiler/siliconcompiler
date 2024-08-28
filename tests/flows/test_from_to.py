import os

import siliconcompiler

import pytest

from siliconcompiler import NodeStatus
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
def test_from_to(gcd_chip):
    # Initial run
    gcd_chip.set('option', 'to', ['syn'])
    gcd_chip.run()

    # Make sure we didn't finish
    assert gcd_chip.find_result('gds', step='write_gds') is None
    # Make sure we ran syn
    assert gcd_chip.find_result('vg', step='syn')
    assert gcd_chip.get('record', 'status', step='import_verilog', index='0') == \
        NodeStatus.SUCCESS
    assert gcd_chip.get('record', 'status', step='syn', index='0') == NodeStatus.SUCCESS

    # Re-run
    gcd_chip.set('option', 'from', ['syn'])
    gcd_chip.set('option', 'to', ['syn'])
    gcd_chip.run()
    assert gcd_chip.find_result('gds', step='write_gds') is None
    assert gcd_chip.find_result('vg', step='syn')

    gcd_chip.set('option', 'from', ['floorplan'])
    gcd_chip.set('option', 'to', ['floorplan'])
    gcd_chip.run()
    assert gcd_chip.find_result('def', step='floorplan')


@pytest.mark.eda
@pytest.mark.quick
def test_from_to_mutliple_starts(gcd_chip, datadir):
    # Initial run
    gcd_chip.input(os.path.join(datadir, 'multiple_frontends', 'binary_4_bit_adder_top.vhd'))
    gcd_chip.input(os.path.join(datadir, 'multiple_frontends', 'top.v'))
    gcd_chip.set('option', 'entrypoint', 'top')
    gcd_chip.set('option', 'entrypoint', 'binary_4_bit_adder_top', step='import_vhdl')
    gcd_chip.set('tool', 'ghdl', 'task', 'convert', 'var', 'extraopts', '-fsynopsys')
    gcd_chip.remove('flowgraph', 'asicflow')
    gcd_chip.use(freepdk45_demo)

    fresh_chip = siliconcompiler.Chip(gcd_chip.design)
    fresh_chip.schema = gcd_chip.schema.copy()

    gcd_chip.set('option', 'to', ['syn'])
    gcd_chip.run()

    assert gcd_chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                        step='syn', index='0') is not None
    report = gcd_chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                          step='syn', index='0')

    # Run a new step from a fresh chip object
    fresh_chip.set('option', 'from', ['floorplan'])
    fresh_chip.set('option', 'to', ['floorplan'])
    fresh_chip.run()
    assert fresh_chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                          step='syn', index='0') == report


@pytest.mark.eda
@pytest.mark.quick
def test_from_to_keep_reports(gcd_chip):
    '''Regression test for making sure that reports from previous steps are
    still mapped when a script is re-run with a from/to.'''
    fresh_chip = siliconcompiler.Chip(gcd_chip.design)
    fresh_chip.schema = gcd_chip.schema.copy()

    # Initial run
    gcd_chip.set('option', 'to', ['syn'])
    gcd_chip.run()
    assert gcd_chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                        step='syn', index='0') is not None
    report = gcd_chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                          step='syn', index='0')

    # Run a new step from a fresh chip object
    fresh_chip.set('option', 'from', ['floorplan'])
    fresh_chip.set('option', 'to', ['floorplan'])
    fresh_chip.run()
    assert fresh_chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                          step='syn', index='0') == report


@pytest.mark.eda
@pytest.mark.quick
def test_old_clean(gcd_chip):
    '''Regression test for making sure that using ['option', 'clean'] in a
    previous run does not affect the behavior of a future run when a script is
    re-run with a partial from/to.'''
    # Initial run
    gcd_chip.set('option', 'clean', False)
    gcd_chip.set('option', 'to', ['syn'])
    gcd_chip.run()
    manifest = os.path.join(gcd_chip.getworkdir(step='syn', index='0'), 'outputs', 'gcd.pkg.json')
    mtime_before = os.path.getmtime(manifest)

    # Run a new step from a fresh chip object
    gcd_chip.set('option', 'clean', True)
    gcd_chip.set('option', 'from', ['syn'])
    gcd_chip.set('option', 'to', ['syn'])
    gcd_chip.run()
    mtime_after = os.path.getmtime(manifest)

    assert mtime_after > mtime_before


@pytest.mark.eda
@pytest.mark.quick
def test_invalid(gcd_chip):
    # Invalid from/to, need to run import first
    gcd_chip.set('option', 'from', ['syn'])
    gcd_chip.set('option', 'to', ['syn'])

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        # Should be caught by check_manifest()
        gcd_chip.run()
