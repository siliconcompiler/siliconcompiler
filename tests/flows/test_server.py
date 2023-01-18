import json
import os
import subprocess
import traceback
import pytest
import time

from unittest.mock import Mock

###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason='Temporary until server update')
def test_gcd_server(gcd_chip):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'])
    time.sleep(3)

    # Mock the _runstep method.
    old__runtask = gcd_chip._runtask
    def mocked_runtask(*args, **kwargs):
        if args[0] == 'import':
            old__runtask(*args)
        else:
            gcd_chip.logger.error('Non-import step run locally in remote job!')
    gcd_chip._runtask = Mock()
    gcd_chip._runtask.side_effect = mocked_runtask

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost', 'port': 8080}))
    gcd_chip.set('option', 'remote', True)
    gcd_chip.set('option', 'credentials', os.path.abspath(tmp_creds))

    # Run the remote job.
    try:
        gcd_chip.run()
    except Exception:
        # Failures will be printed, and noted in the following assert.
        traceback.print_exc()

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

if __name__ == "__main__":
    from tests.fixtures import gcd_chip
    if os.path.isdir('local_server_work'):
        os.rmdir('local_server_work')
    test_gcd_server(gcd_chip())
