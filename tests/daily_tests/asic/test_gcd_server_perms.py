import os
import re
import subprocess
from tests.fixtures import test_wrapper

###########################
def test_gcd_server_permutations():
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local',
                                 '-port', '8081'],
                                stdout = subprocess.DEVNULL)

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/daily_tests/asic')] + '/examples/gcd/'
    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-constraint', gcd_ex_dir + '/gcd.sdc',
                    '-permutations', gcd_ex_dir + '/2jobs.py',
                    '-remote_addr', 'localhost',
                    '-remote_port', '8081',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS/SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/job2/export/outputs/gcd.gds')
