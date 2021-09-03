import json
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
    with open('../test.log', 'w') as f:
        srv_proc = subprocess.Popen(['sc-server',
                                     '-nfs_mount', './local_server_work',
                                     '-cluster', 'local',
                                     '-port', '8082'],
                                    stdout = f)

    # Find an absolute path to the example design.
    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/daily_tests/asic')] + '/examples/gcd/'
    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    # Run an 'sc' step which stops at the 'floorplan' step.
    sproc = subprocess.run(['sc',
                            gcd_ex_dir + '/gcd.v',
                            '-design', 'gcd',
                            '-target', 'freepdk45_asicflow',
                            '-steplist', 'import',
                            '-steplist', 'syn',
                            '-steplist', 'floorplan',
                            '-asic_diearea', "(0,0)",
                            '-asic_diearea', "(100.13,100.8)",
                            '-asic_corearea', "(10.07,11.2)",
                            '-asic_corearea', "(90.25,91)",
                            '-constraint', gcd_ex_dir + '/gcd.sdc',
                            '-remote_addr', 'localhost',
                            '-remote_port', '8082',
                            '-loglevel', 'NOTSET'],
                           stdout = subprocess.PIPE)

    # Run another 'sc' step to resume, complete, and delete the prior job run.
    sproc = subprocess.run(['sc',
                            '-cfg', 'build/gcd/job0/floorplan0/sc_manifest.json',
                            '-dir', 'build/',
                            '-steplist', 'synopt',
                            '-steplist', 'place',
                            '-steplist', 'route',
                            '-steplist', 'dfm',
                            '-steplist', 'export',
                            '-remote_addr', 'localhost',
                            '-remote_port', '8082',
                            '-loglevel', 'NOTSET'],
                           stdout = subprocess.PIPE)

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/export0/outputs/gcd.gds')
