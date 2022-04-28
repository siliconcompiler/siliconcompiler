import siliconcompiler

import json
import os
import subprocess
import time

import pytest

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

    chip = siliconcompiler.Chip()
    chip.set('design', design)
    for index in ('0', '1'):
        chip.set('read', 'netlist', 'place', index, netlist)
        chip.set('read', 'def', 'place', index, def_file)
    chip.set('mode', 'asic')
    chip.set('quiet', True)
    chip.set('jobname', jobname)

    chip.load_target('freepdk45_demo')

    flow = 'test'
    # no-op import since we're not preprocessing source files
    chip.node(flow, 'import', 'join')

    chip.node(flow, 'place', 'openroad', index='0')
    chip.node(flow, 'place', 'openroad', index='1')

    chip.edge(flow, 'import', 'place', head_index='0')
    chip.edge(flow, 'import', 'place', head_index='1')

    # Illegal value, so this branch will fail!
    chip.set('eda', 'openroad', 'variable', 'place', '0', 'place_density', 'asdf')
    # Legal value, so this branch should succeed
    chip.set('eda', 'openroad', 'variable', 'place', '1', 'place_density', '0.5')

    # Perform minimum
    chip.node(flow, 'placemin', 'minimum')
    chip.edge(flow, 'place', 'placemin', tail_index='0')
    chip.edge(flow, 'place', 'placemin', tail_index='1')

    chip.node(flow, 'cts', 'openroad')
    chip.edge(flow, 'placemin', 'cts')

    chip.set('steplist', steplist)
    chip.set('flow', flow)

    chip.run()

    chip.summary()

    assert chip.get('flowstatus', 'place', '0', 'status') == siliconcompiler.TaskStatus.ERROR
    assert chip.get('flowstatus', 'place', '1', 'status') == siliconcompiler.TaskStatus.SUCCESS

@pytest.mark.eda
@pytest.mark.quick
def test_long_branch(scroot):
    '''Test for this case:

    import0 --> place0 [fail] --> cts0
            \-> place1 [ ok ] --> cts1
    '''
    netlist = os.path.join(scroot, 'tests', 'data', 'oh_fifo_sync_freepdk45.vg')
    def_file = os.path.join(scroot, 'tests', 'data', 'oh_fifo_sync.def')

    jobname = 'issue_repro'
    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip()
    chip.set('design', design)
    for index in ('0', '1'):
        chip.set('read', 'netlist', 'place', index, netlist)
        chip.set('read', 'def', 'place', index, def_file)
    chip.set('mode', 'asic')
    chip.set('quiet', True)
    chip.set('jobname', jobname)

    chip.load_target('freepdk45_demo')

    flow = 'test'
    # no-op import since we're not preprocessing source files
    chip.node(flow, 'import', 'join')

    chip.node(flow, 'place', 'openroad', index='0')
    chip.node(flow, 'place', 'openroad', index='1')

    chip.edge(flow, 'import', 'place', head_index='0')
    chip.edge(flow, 'import', 'place', head_index='1')

    # Illegal value, so this branch will fail!
    chip.set('eda', 'openroad', 'variable', 'place', '0', 'place_density', 'asdf')
    # Legal value, so this branch should succeed
    chip.set('eda', 'openroad', 'variable', 'place', '1', 'place_density', '0.5')

    chip.node(flow, 'cts', 'openroad', index='0')
    chip.node(flow, 'cts', 'openroad', index='1')
    chip.edge(flow, 'place', 'cts', tail_index='0', head_index='0')
    chip.edge(flow, 'place', 'cts', tail_index='1', head_index='1')

    chip.set('flow', flow)

    chip.run()

    assert chip.get('flowstatus', 'place', '0', 'status') == siliconcompiler.TaskStatus.ERROR
    assert chip.get('flowstatus', 'place', '1', 'status') == siliconcompiler.TaskStatus.SUCCESS

@pytest.mark.eda
@pytest.mark.quick
def test_remote(scroot):
    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-port', '8081',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'])
    time.sleep(3)

    chip = siliconcompiler.Chip()

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost', 'port': 8081}))
    chip.set('remote', True)
    chip.set('credentials', os.path.abspath(tmp_creds))

    src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    chip.set('design', 'gcd')
    chip.set('source', src)

    chip.set('flowarg', 'place_np', '2')
    # Illegal value, so this branch will fail!
    chip.set('eda', 'openroad', 'variable', 'place', '0', 'place_density', 'asdf')
    # Legal value, so this branch should succeed
    chip.set('eda', 'openroad', 'variable', 'place', '1', 'place_density', '0.5')

    chip.load_target('freepdk45_demo')

    chip.run()

    # Kill the server process.
    srv_proc.kill()

    assert chip.get('flowstatus', 'place', '0', 'status') == siliconcompiler.TaskStatus.ERROR
    assert chip.get('flowstatus', 'place', '1', 'status') == siliconcompiler.TaskStatus.SUCCESS

    chip.summary()
