import siliconcompiler
from siliconcompiler import NodeStatus

import json
import os
import subprocess
import time

import pytest

from siliconcompiler.tools.openroad import place
from siliconcompiler.tools.openroad import cts

from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin import minimum


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('steplist', [
    ['import', 'place'],
    ['import', 'place', 'placemin'],
    ['import', 'place', 'placemin', 'cts']
])
def test_flowstatus(scroot, steplist):
    netlist = os.path.join(scroot, 'tests', 'data', 'oh_fifo_sync_freepdk45.vg')
    def_file = os.path.join(scroot, 'tests', 'data', 'oh_fifo_sync.def')

    jobname = 'issue_repro'
    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip(design)
    chip.input(netlist)
    chip.input(def_file)
    chip.set('option', 'mode', 'asic')
    chip.set('option', 'quiet', True)
    chip.set('option', 'jobname', jobname)

    chip.load_target('freepdk45_demo')

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

    chip.set('option', 'steplist', steplist)
    chip.set('option', 'flow', flow)

    chip.run()

    chip.summary()

    assert chip.get('flowgraph', flow, 'place', '0', 'status') == NodeStatus.ERROR
    assert chip.get('flowgraph', flow, 'place', '1', 'status') == NodeStatus.SUCCESS


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
    chip.set('option', 'mode', 'asic')
    chip.set('option', 'quiet', True)
    chip.set('option', 'jobname', jobname)

    chip.load_target('freepdk45_demo')

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

    assert chip.get('flowgraph', flow, 'place', '0', 'status') == NodeStatus.ERROR
    assert chip.get('flowgraph', flow, 'place', '1', 'status') == NodeStatus.SUCCESS


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason='Temporary until server update')
def test_remote(scroot):
    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-port', '8081',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'])
    time.sleep(3)

    chip = siliconcompiler.Chip('gcd')

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost', 'port': 8081}))
    chip.set('option', 'remote', True)
    chip.set('option', 'credentials', os.path.abspath(tmp_creds))

    src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')

    chip.input(src)

    chip.set('arg', 'flow', 'place_np', '2')
    # Illegal value, so this branch will fail!
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
             step='place', index='0')
    # Legal value, so this branch should succeed
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.5',
             step='place', index='1')

    chip.load_target('freepdk45_demo')
    flow = chip.get('option', 'flow')
    chip.run()

    # Kill the server process.
    srv_proc.kill()

    assert chip.get('flowgraph', flow, 'place', '0', 'status') == NodeStatus.ERROR
    assert chip.get('flowgraph', flow, 'place', '1', 'status') == NodeStatus.SUCCESS

    chip.summary()
