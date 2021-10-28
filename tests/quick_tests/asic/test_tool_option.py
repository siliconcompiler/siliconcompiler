import os
import siliconcompiler
import pytest

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_tool_option():
    '''Regresttion test for checker being too strict and preventing user from
    setting tool options. Doesn't check any outputs, just that this doesn't fail
    early.'''
    chip = siliconcompiler.Chip()

    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/quick_tests/asic')] + '/examples/gcd/'

    # Inserting value into configuration
    chip.set('design', 'gcd', clobber=True)
    chip.set('target', 'asicflow_freepdk45')
    chip.add('source', gcd_ex_dir + 'gcd.v')
    chip.set('clock', 'clock_name', 'pin', 'clk')
    chip.add('constraint', gcd_ex_dir + 'gcd.sdc')
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.set('quiet', 'true')
    chip.set('relax', 'true')
    chip.set('flowarg', 'place_np', ['2'])
    chip.target()

    chip.set('eda', 'openroad', 'place', '0', 'option', 'place_density', '0.15')
    chip.set('eda', 'openroad', 'place', '1', 'option', 'place_density', '0.3')

    # No need to run beyond place, we just want to check that setting place_density
    # doesn't break anything.
    steplist = [
        'import',
        'syn',
        'synmin',
        'floorplan',
        'floorplanmin',
        'physyn',
        'physynmin',
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
def chip():
    '''Chip fixture to reuse for next few tests.

    This chip is configured to run two parallel 'place' steps. The user of this
    fixture must add the step used to join the two!
    '''
    localdir = os.path.dirname(os.path.abspath(__file__))

    netlist = f"{localdir}/../../data/oh_fifo_sync_freepdk45.vg"
    def_file = f"{localdir}/../../data/oh_fifo_sync.def"

    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip()
    chip.set('design', design)
    chip.set('netlist', netlist)
    chip.set('asic', 'def', def_file)
    chip.set('mode', 'asic')
    chip.set('quiet', True)
    chip.target('freepdk45')

    # no-op import since we're not preprocessing source files
    chip.set('flowgraph', 'import', '0', 'function', 'step_join')

    chip.set('flowgraph', 'place', '0', 'tool', 'openroad')
    chip.set('flowgraph', 'place', '0', 'input', 'import0')

    chip.set('flowgraph', 'place', '1', 'tool', 'openroad')
    chip.set('flowgraph', 'place', '1', 'input', 'import0')

    return chip

def test_failed_branch_step_min(chip):
    '''Test that a step_minimum will allow failed inputs, as long as at least
    one passes.'''

    # Illegal value, so this branch will fail!
    chip.set('eda', 'openroad', 'place', '0', 'option', 'place_density', 'asdf')
    # Legal value, so this branch should succeed
    chip.set('eda', 'openroad', 'place', '1', 'option', 'place_density', '0.5')

    # Perform minimum
    chip.set('flowgraph', 'placemin', '0', 'function', 'step_minimum')
    chip.set('flowgraph', 'placemin', '0', 'input', ['place0', 'place1'])

    chip.run()

    assert chip.get('flowstatus', 'place', '0', 'error') == 1
    assert chip.get('flowstatus', 'place', '1', 'error') == 0

    # check that compilation succeeded
    assert chip.find_result('def', step='placemin') is not None

def test_all_failed_step_min(chip):
    '''Test that a step_minimum will fail if both branches have errors.'''


    # Illegal values, so both branches should fail
    chip.set('eda', 'openroad', 'place', '0', 'option', 'place_density', 'asdf')
    chip.set('eda', 'openroad', 'place', '1', 'option', 'place_density', 'asdf')

    # Perform minimum
    chip.set('flowgraph', 'placemin', '0', 'function', 'step_minimum')
    chip.set('flowgraph', 'placemin', '0', 'input', ['place0', 'place1'])

    # Expect that command exits early
    with pytest.raises(SystemExit):
        chip.run()

    # check that compilation failed
    assert chip.find_result('def', step='placemin') is None

def test_branch_failed_step_join(chip):
    '''Test that a step_join will fail if one branch has errors.'''

    # Illegal values, so branch should fail
    chip.set('eda', 'openroad', 'place', '0', 'option', 'place_density', 'asdf')
    # Legal value, so branch should succeed
    chip.set('eda', 'openroad', 'place', '1', 'option', 'place_density', '0.5')

    # Perform join
    chip.set('flowgraph', 'placemin', '0', 'function', 'step_join')
    chip.set('flowgraph', 'placemin', '0', 'input', ['place0', 'place1'])

    # Expect that command exits early
    with pytest.raises(SystemExit):
        chip.run()

    # check that compilation failed
    assert chip.find_result('def', step='placemin') is None

if __name__ == "__main__":
    test_tool_option()
