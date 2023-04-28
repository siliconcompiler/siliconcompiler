import json
import os
import subprocess
import traceback
import pytest
import time

from unittest.mock import Mock

SERVER_STARTUP_DELAY = 10

@pytest.fixture
def gcd_remote_test(gcd_chip, unused_tcp_port):

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-port', str(unused_tcp_port),
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'slurm'])
    time.sleep(SERVER_STARTUP_DELAY)

    # Mock the _runstep method.
    old__runtask = gcd_chip._runtask
    def mocked_runtask(*args, **kwargs):
        if args[0] == 'import':
            old__runtask(*args)
        else:
            gcd_chip.logger.error('Non-import step run locally in remote job!')
    gcd_chip._runtask = Mock()
    gcd_chip._runtask.side_effect = mocked_runtask

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost',
                                        'port': unused_tcp_port}))
    gcd_chip.set('option', 'remote', True)
    gcd_chip.set('option', 'credentials', os.path.abspath(tmp_creds))

    gcd_chip.set('option', 'nodisplay', True)

    try:
        yield gcd_chip
    except Exception as e:
        # Kill the server process.
        srv_proc.kill()
        # Re-raise the exception.
        raise e

    # Kill the server process.
    srv_proc.kill()


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_gcd_server(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test

    # Run the remote job.
    try:
        gcd_chip.run()
    except Exception:
        # Failures will be printed, and noted in the following assert.
        traceback.print_exc()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
