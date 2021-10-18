import os
import re
import subprocess

if __name__ != "__main__":
    from tests.fixtures import *
else:
    from tests.utils import *

###########################
def test_gcd_server_slurm(gcd_chip):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
       The server uses a slurm cluster to delegate job steps in this test.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'slurm',
                                 '-port', '8089'])

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    gcd_chip.set('remote', 'addr', 'localhost')
    gcd_chip.set('remote', 'port', 8089)
    gcd_chip.run()

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS was generated and returned.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

if __name__ == "__main__":
    test_gcd_server_slurm(gcd_chip())
