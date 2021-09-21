import base64
import json
import os
import re
import subprocess
from tests.fixtures import test_wrapper

###########################
def test_gcd_server_slurm_authenticated():
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
       Use authentication and encryption features.
       The server uses a slurm cluster to delegate job steps in this test.
    '''

    # Collect relevant file paths.
    root_dir = os.path.abspath(__file__)
    root_dir = root_dir[:root_dir.rfind('/tests/daily_tests/asic')]
    gcd_ex_dir = root_dir + '/examples/gcd/'

    # Create a JSON file with a test user / key.
    os.mkdir('local_server_work')
    with open(root_dir + '/tests/insecure_ci_keypair.pub', 'r') as pubkey:
        with open('local_server_work/users.json', 'w') as f:
            f.write(json.dumps({'users': [{
                'username': 'test_user',
                'pub_key': pubkey.read(),
            }]}))

    # Start running an sc-server instance.
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'slurm',
                                 '-port', '8090',
                                 '-auth'],
                                stdout = subprocess.DEVNULL)

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-target', 'freepdk45_asicflow',
                    '-asic_diearea', '0,0,100.13,100.8',
                    '-asic_corearea', '10.07,11.2,90.25,91',
                    '-constraint', gcd_ex_dir + '/gcd.sdc',
                    '-remote_addr', 'localhost',
                    '-remote_port', '8090',
                    '-remote_user', 'test_user',
                    '-remote_key', root_dir + '/tests/insecure_ci_keypair',
                    '-relax',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/export0/outputs/gcd.gds')

###########################
def test_gcd_server_slurm_not_authenticated():
    '''Basic sc-server test: Run a local instance of a server, and attempt to
       authenticate a user with an invalid key. The remote run should fail.
       The server uses a slurm cluster to delegate job steps in this test.
    '''

    # Collect relevant file paths.
    root_dir = os.path.abspath(__file__)
    root_dir = root_dir[:root_dir.rfind('/tests/daily_tests/asic')]
    gcd_ex_dir = root_dir + '/examples/gcd/'

    # Create a JSON file with a test user / key.
    # This key is random, so it shouldn't match the stored test keypair.
    os.mkdir('local_server_work')
    with open('local_server_work/users.json', 'w') as f:
        f.write(json.dumps({'users': [{
            'username': 'test_user',
            'pub_key': 'ssh-rsa ' + base64.b64encode(os.urandom(2048)).decode(),
        }]}))

    # Start running an sc-server instance.
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'slurm',
                                 '-port', '8091',
                                 '-auth'],
                                stdout = subprocess.DEVNULL)

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-target', 'freepdk45_asicflow',
                    '-asic_diearea', '0,0,100.13,100.8',
                    '-asic_corearea', '10.07,11.2,90.25,91',
                    '-constraint', gcd_ex_dir + '/gcd.sdc',
                    '-remote_addr', 'localhost',
                    '-remote_port', '8091',
                    '-remote_user', 'test_user',
                    '-remote_key', root_dir + '/tests/insecure_ci_keypair',
                    '-relax',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS and SVG files were generated and returned.
    assert (not os.path.isfile('build/gcd/job0/export0/outputs/gcd.gds'))
