import os
import re
import subprocess
from tests.fixtures import test_wrapper

###########################
def test_gcd_server():
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'],
                                stdout = subprocess.DEVNULL)

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/asic')] + '/examples/gcd/'
    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-target', 'freepdk45',
                    '-asic_diesize', '0 0 100.13 100.8',
                    '-asic_coresize', '10.07 11.2 90.25 91',
                    '-constraint', gcd_ex_dir + '/constraint.sdc',
                    '-remote_addr', 'localhost',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Kill the server process.
    srv_proc.kill()

    # Find the job hash of the generated job.
    # (Job hashes are 32-character lowercase hex strings)
    for d in os.listdir('.'):
        if (re.match('[0-9a-f]*', d)) and (len(d) == 32):
            job_hash = d
            break
    # Verify that a GDS file was generated and returned in the server's results.
    assert os.path.isfile(job_hash + '/gcd/job1/export/outputs/gcd.gds')

