import os
import siliconcompiler
import pytest

from siliconcompiler.tools.openroad import place

from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin import join
from siliconcompiler.tools.builtin import minimum

from siliconcompiler import NodeStatus


@pytest.mark.eda
@pytest.mark.quick
def test_tool_option(scroot):
    '''Regression test for checker being too strict and preventing user from
    setting tool options. Doesn't check any outputs, just that this doesn't fail
    early.'''
    chip = siliconcompiler.Chip('gcd')

    gcd_ex_dir = os.path.join(scroot, 'examples', 'gcd')

    # Inserting value into configuration
    chip.set('design', 'gcd', clobber=True)
    chip.input(os.path.join(gcd_ex_dir, 'gcd.v'))
    chip.input(os.path.join(gcd_ex_dir, 'gcd.sdc'))
    chip.set('constraint', 'outline', [(0, 0), (100.13, 100.8)])
    chip.set('constraint', 'corearea', [(10.07, 11.2), (90.25, 91)])
    chip.set('option', 'quiet', 'true')
    chip.set('option', 'relax', 'true')
    chip.set('option', 'novercheck', 'true')
    chip.load_target('freepdk45_demo', place_np=2)

    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.4',
             step='place', index='0')
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.3',
             step='place', index='1')

    # No need to run beyond place, we just want to check that setting place_density
    # doesn't break anything.
    steplist = [
        'import',
        'syn',
        'floorplan',
        'place',
        'placemin'
    ]
    chip.set('option', 'steplist', steplist)

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
    def_file = os.path.join(datadir, 'oh_fifo_sync.def')

    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip(design)
    chip.input(def_file)
    chip.set('option', 'quiet', True)
    chip.set('option', 'novercheck', 'true')
    chip.load_target('freepdk45_demo')

    # Important: set up our own flow instead of using asicflow.
    chip.set('option', 'flow', 'test')
    flow = chip.get('option', 'flow')

    # no-op import since we're not preprocessing source files
    chip.node(flow, 'import', nop)

    chip.node(flow, 'place', place, index=0)
    chip.edge(flow, 'import', 'place', head_index=0)

    chip.node(flow, 'place', place, index=1)
    chip.edge(flow, 'import', 'place', head_index=1)

    return chip


@pytest.mark.eda
@pytest.mark.quick
def test_failed_branch_min(chip):
    '''Test that a minimum will allow failed inputs, as long as at least
    one passes.'''
    flow = chip.get('option', 'flow')

    # Illegal value, so this branch will fail!
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
             step='place', index='0')
    # Legal value, so this branch should succeed
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.5',
             step='place', index='1')

    # Perform minimum
    chip.node(flow, 'placemin', minimum)
    chip.edge(flow, 'place', 'placemin', tail_index=0)
    chip.edge(flow, 'place', 'placemin', tail_index=1)

    chip.run()

    assert chip.get('history', 'job0', 'flowgraph', flow, 'place', '0', 'status') == \
        NodeStatus.ERROR
    assert chip.get('history', 'job0', 'flowgraph', flow, 'place', '1', 'status') == \
        NodeStatus.SUCCESS

    # check that compilation succeeded
    assert chip.find_result('def', step='placemin') is not None

    # Ensure that summary/report generation can handle failed branch without
    # error.
    chip.set('flowgraph', flow, 'place', '0', 'weight', 'errors', 0)
    chip.set('flowgraph', flow, 'place', '0', 'weight', 'warnings', 0)
    chip.summary()


@pytest.mark.eda
@pytest.mark.quick
def test_all_failed_min(chip):
    '''Test that a minimum will fail if both branches have errors.'''

    flow = chip.get('option', 'flow')

    # Illegal values, so both branches should fail
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf')

    # Perform minimum
    chip.node(flow, 'placemin', minimum)
    chip.edge(flow, 'place', 'placemin', tail_index=0)
    chip.edge(flow, 'place', 'placemin', tail_index=1)

    # Expect that command exits early
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.run()

    # check that compilation failed
    assert chip.find_result('def', step='placemin') is None


@pytest.mark.eda
@pytest.mark.quick
def test_branch_failed_join(chip):
    '''Test that a join will fail if one branch has errors.'''

    flow = chip.get('option', 'flow')

    # Illegal values, so branch should fail
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
             step='place', index='0')
    # Legal value, so branch should succeed
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.5',
             step='place', index='1')

    # Perform join
    chip.node(flow, 'placemin', join)
    chip.edge(flow, 'place', 'placemin', tail_index=0)
    chip.edge(flow, 'place', 'placemin', tail_index=1)

    # Expect that command exits early
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.run()

    # check that compilation failed
    assert chip.find_result('def', step='placemin') is None


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_tool_option(scroot())
