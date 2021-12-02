import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_tool_option(scroot):
    '''Regression test for checker being too strict and preventing user from
    setting tool options. Doesn't check any outputs, just that this doesn't fail
    early.'''
    chip = siliconcompiler.Chip()

    gcd_ex_dir = os.path.join(scroot, 'examples', 'gcd')

    # Inserting value into configuration
    chip.set('design', 'gcd', clobber=True)
    chip.set('target', 'asicflow_freepdk45')
    chip.add('source', os.path.join(gcd_ex_dir, 'gcd.v'))
    chip.set('clock', 'core_clock', 'pin', 'clk')
    chip.set('clock', 'core_clock', 'period', 2)
    chip.add('constraint', os.path.join(gcd_ex_dir, 'gcd_noclock.sdc'))
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.set('quiet', 'true')
    chip.set('relax', 'true')
    chip.set('flowarg', 'place_np', ['2'])
    chip.target()

    chip.set('eda', 'openroad', 'place', '0', 'variable', 'place_density', '0.15')
    chip.set('eda', 'openroad', 'place', '1', 'variable', 'place_density', '0.3')

    # No need to run beyond place, we just want to check that setting place_density
    # doesn't break anything.
    steplist = [
        'import',
        'syn',
        'floorplan',
        'physyn',
        'place',
        'placemin'
    ]
    chip.set('steplist', steplist)

    # Run the chip's build process synchronously.
    chip.run()

    # Make sure we ran and got results from two place steps
    assert chip.find_result('pkg.json', step='place', index='0') is not None
    assert chip.find_result('pkg.json', step='place', index='1') is not None

@pytest.fixture
def chip(scroot):
    '''Chip fixture to reuse for next few tests.

    This chip is configured to run two parallel 'place' steps. The user of this
    fixture must add the step used to join the two!
    '''

    datadir = os.path.join(scroot, 'tests', 'data')
    netlist = os.path.join(datadir, 'oh_fifo_sync_freepdk45.vg')
    def_file = os.path.join(datadir, 'oh_fifo_sync.def')

    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip()
    chip.set('design', design)
    chip.set('netlist', netlist)
    chip.set('asic', 'def', def_file)
    chip.set('mode', 'asic')
    chip.set('quiet', True)
    chip.target('freepdk45')

    # no-op import since we're not preprocessing source files
    chip.set('flowgraph', 'import', '0', 'tool', 'join')

    chip.set('flowgraph', 'place', '0', 'tool', 'openroad')
    chip.set('flowgraph', 'place', '0', 'input', ('import','0'))

    chip.set('flowgraph', 'place', '1', 'tool', 'openroad')
    chip.set('flowgraph', 'place', '1', 'input', ('import','0'))

    return chip

@pytest.mark.eda
@pytest.mark.quick
def test_failed_branch_min(chip):
    '''Test that a minimum will allow failed inputs, as long as at least
    one passes.'''

    # Illegal value, so this branch will fail!
    chip.set('eda', 'openroad', 'place', '0', 'variable', 'place_density', 'asdf')
    # Legal value, so this branch should succeed
    chip.set('eda', 'openroad', 'place', '1', 'variable', 'place_density', '0.5')

    # Perform minimum
    chip.set('flowgraph', 'placemin', '0', 'tool', 'minimum')
    chip.set('flowgraph', 'placemin', '0', 'input', [('place','0'), ('place','1')])

    chip.run()

    assert chip.get('flowstatus', 'place', '0', 'error') == 1
    assert chip.get('flowstatus', 'place', '1', 'error') == 0

    # check that compilation succeeded
    assert chip.find_result('def', step='placemin') is not None

@pytest.mark.eda
@pytest.mark.quick
def test_all_failed_min(chip):
    '''Test that a minimum will fail if both branches have errors.'''


    # Illegal values, so both branches should fail
    chip.set('eda', 'openroad', 'place', '0', 'variable', 'place_density', 'asdf')
    chip.set('eda', 'openroad', 'place', '1', 'variable', 'place_density', 'asdf')

    # Perform minimum
    chip.set('flowgraph', 'placemin', '0', 'tool', 'minimum')
    chip.set('flowgraph', 'placemin', '0', 'input', [('place','0'), ('place','1')])

    # Expect that command exits early
    with pytest.raises(SystemExit):
        chip.run()

    # check that compilation failed
    assert chip.find_result('def', step='placemin') is None

@pytest.mark.eda
@pytest.mark.quick
def test_branch_failed_join(chip):
    '''Test that a join will fail if one branch has errors.'''

    # Illegal values, so branch should fail
    chip.set('eda', 'openroad', 'place', '0', 'variable', 'place_density', 'asdf')
    # Legal value, so branch should succeed
    chip.set('eda', 'openroad', 'place', '1', 'variable', 'place_density', '0.5')

    # Perform join
    chip.set('flowgraph', 'placemin', '0', 'tool', 'join')
    chip.set('flowgraph', 'placemin', '0', 'input', [('place','0'), ('place','1')])

    # Expect that command exits early
    with pytest.raises(SystemExit):
        chip.run()

    # check that compilation failed
    assert chip.find_result('def', step='placemin') is None

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_tool_option(scroot())
