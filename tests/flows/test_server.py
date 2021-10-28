import os
import subprocess
import traceback
import pytest

from unittest.mock import Mock

###########################
@pytest.mark.eda
@pytest.mark.quick
def test_gcd_server(gcd_chip):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'])

    # Mock the _runstep method.
    old__runstep = gcd_chip._runstep
    def mocked_runstep(*args, **kwargs):
        if args[0] == 'import':
            old__runstep(*args)
        else:
            gcd_chip.logger.error('Non-import step run locally in remote job!')
    gcd_chip._runstep = Mock()
    gcd_chip._runstep.side_effect = mocked_runstep

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    gcd_chip.set('remote', 'addr', 'localhost')
    gcd_chip.set('remote', 'port', '8080')

    # Run the remote job.
    try:
        gcd_chip.run()
    except:
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
