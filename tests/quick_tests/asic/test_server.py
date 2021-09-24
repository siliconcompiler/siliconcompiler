import os
import re
import subprocess

if __name__ != "__main__":
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
                                 '-cluster', 'local'])

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/quick_tests/asic')] + '/examples/gcd/'
    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-target', 'asicflow_freepdk45',
                    '-asic_diearea', "(0,0)",
                    '-asic_diearea', "(100.13,100.8)",
                    '-asic_corearea', "(10.07,11.2)",
                    '-asic_corearea', "(90.25,91)",
                    '-constraint', gcd_ex_dir + '/gcd.sdc',
                    '-remote_addr', 'localhost',
                    '-remote_port', '8080',
                    '-relax'])

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/export0/outputs/gcd.gds')

if __name__ == "__main__":
    test_gcd_server()
