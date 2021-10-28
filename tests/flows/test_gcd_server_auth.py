import base64
import json
import os
import subprocess

import pytest

###########################
@pytest.mark.eda
def test_gcd_server_authenticated(gcd_chip, scroot):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
       Use authentication and encryption features.
    '''

    datadir = os.path.join(scroot, 'tests', 'data')

    # Create a JSON file with a test user / key.
    user_pwd = 'insecure_ci_password'
    os.mkdir('local_server_work')
    with open(os.path.join(datadir, 'insecure_ci_keypair.pub'), 'r') as pubkey:
        with open(os.path.join(datadir, 'insecure_ci_keypair'), 'r') as privkey:
            with open('local_server_work/users.json', 'w') as f:
                # Passwords should never be stored in plaintext in a production
                # environment, but the development server is a minimal
                # implementation of the API, intended only for testing.
                f.write(json.dumps({'users': [{
                    'username': 'test_user',
                    'pub_key': pubkey.read(),
                    'priv_key': privkey.read(),
                    'password': user_pwd,
                }]}))

    # Start running an sc-server instance.
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local',
                                 '-port', '8085',
                                 '-auth'],
                                stdout = subprocess.DEVNULL)

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    # Add remote parameters.
    gcd_chip.set('remote', 'addr', 'localhost')
    gcd_chip.set('remote', 'port', '8085')
    gcd_chip.set('remote', 'user', 'test_user')
    gcd_chip.set('remote', 'password', user_pwd)

    # Run remote build.
    gcd_chip.run()

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS file was generated and returned.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

###########################
@pytest.mark.eda
def test_gcd_server_not_authenticated(gcd_chip, scroot):
    '''Basic sc-server test: Run a local instance of a server, and attempt to
       authenticate a user with an invalid key. The remote run should fail.
    '''

    datadir = os.path.join(scroot, 'tests', 'data')

    # Create a JSON file with a test user / key.
    # This key is random, so it shouldn't match the stored test keypair.
    user_pwd = 'insecure_ci_password'
    os.mkdir('local_server_work')
    with open('local_server_work/users.json', 'w') as f:
        with open(os.path.join(datadir, 'insecure_ci_keypair'), 'r') as privkey:
            f.write(json.dumps({'users': [{
                'username': 'test_user',
                'pub_key': 'ssh-rsa ' + base64.b64encode(os.urandom(2048)).decode(),
                'priv_key': privkey.read(),
                'password': user_pwd,
        }]}))

    # Start running an sc-server instance.
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local',
                                 '-port', '8086',
                                 '-auth'],
                                stdout = subprocess.DEVNULL)

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    # Add remote parameters.
    gcd_chip.set('remote', 'addr', 'localhost')
    gcd_chip.set('remote', 'port', '8086')
    gcd_chip.set('remote', 'user', 'test_user')
    gcd_chip.set('remote', 'password', 'wrong_password')

    # Run remote build. It may fail, so catch SystemExit exceptions.
    try:
        gcd_chip.run()
    except SystemExit:
        pass

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS was not generated.
    assert (not os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds'))
