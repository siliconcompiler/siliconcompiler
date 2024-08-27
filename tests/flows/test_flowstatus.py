import siliconcompiler
from siliconcompiler import NodeStatus

import os

import pytest

from siliconcompiler.tools.openroad import place
from siliconcompiler.tools.openroad import cts

from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin import minimum
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('to', ['placemin', 'cts'])
def test_flowstatus(scroot, to):
    netlist = os.path.join(scroot, 'tests', 'data', 'oh_fifo_sync_freepdk45.vg')
    def_file = os.path.join(scroot, 'tests', 'data', 'oh_fifo_sync.def')

    jobname = 'issue_repro'
    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip(design)
    chip.input(netlist)
    chip.input(def_file)
    chip.set('option', 'quiet', True)
    chip.set('option', 'jobname', jobname)

    chip.load_target(freepdk45_demo)

    flow = 'test'
    # no-op import since we're not preprocessing source files
    chip.node(flow, 'import', nop)

    chip.node(flow, 'place', place, index='0')
    chip.node(flow, 'place', place, index='1')

    chip.edge(flow, 'import', 'place', head_index='0')
    chip.edge(flow, 'import', 'place', head_index='1')

    # Illegal value, so this branch will fail!
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
             step='place', index='0')
    # Legal value, so this branch should succeed
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.5',
             step='place', index='1')

    # Perform minimum
    chip.node(flow, 'placemin', minimum)
    chip.edge(flow, 'place', 'placemin', tail_index='0')
    chip.edge(flow, 'place', 'placemin', tail_index='1')

    chip.node(flow, 'cts', cts)
    chip.edge(flow, 'placemin', 'cts')

    chip.set('option', 'to', to)
    chip.set('option', 'flow', flow)

    chip.run()

    chip.summary()

    assert chip.get('record', 'status', step='place', index='0') == NodeStatus.ERROR
    assert chip.get('record', 'status', step='place', index='1') == NodeStatus.SUCCESS


@pytest.mark.eda
@pytest.mark.quick
def test_long_branch(scroot):
    r'''
    Test for this case:

    import0 --> place0 [fail] --> cts0
            \-> place1 [ ok ] --> cts1
    '''
    netlist = os.path.join(scroot, 'tests', 'data', 'oh_fifo_sync_freepdk45.vg')
    def_file = os.path.join(scroot, 'tests', 'data', 'oh_fifo_sync.def')

    jobname = 'issue_repro'
    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip(design)
    chip.input(netlist)
    chip.input(def_file)
    chip.set('option', 'quiet', True)
    chip.set('option', 'jobname', jobname)

    chip.load_target(freepdk45_demo)

    flow = 'test'
    # no-op import since we're not preprocessing source files
    chip.node(flow, 'import', nop)

    chip.node(flow, 'place', place, index='0')
    chip.node(flow, 'place', place, index='1')

    chip.edge(flow, 'import', 'place', head_index='0')
    chip.edge(flow, 'import', 'place', head_index='1')

    # Illegal value, so this branch will fail!
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
             step='place', index='0')
    # Legal value, so this branch should succeed
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.5',
             step='place', index='1')

    chip.node(flow, 'cts', cts, index='0')
    chip.node(flow, 'cts', cts, index='1')
    chip.edge(flow, 'place', 'cts', tail_index='0', head_index='0')
    chip.edge(flow, 'place', 'cts', tail_index='1', head_index='1')

    chip.set('option', 'flow', flow)

    chip.run()

    assert chip.get('record', 'status', step='cts', index='0') == NodeStatus.ERROR
    assert chip.get('record', 'status', step='cts', index='1') == NodeStatus.SUCCESS
