from siliconcompiler.apps import sc_remote
import json
import os
import subprocess
import time


###########################
def test_sc_remote_noauth(monkeypatch, unused_tcp_port):
    '''Basic sc-remote test: Call with no user credentials and no arguments.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local',
                                 '-port', str(unused_tcp_port)])
    time.sleep(10)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost',
                                        'port': unused_tcp_port,
                                        }))

    monkeypatch.setattr("sys.argv", ['sc-remote', '-credentials', '.test_remote_cfg'])
    retcode = sc_remote.main()

    # Kill the server process.
    srv_proc.kill()

    assert retcode == 0


###########################
def test_sc_remote_auth(monkeypatch, unused_tcp_port):
    '''Basic sc-remote test: Call with an authenticated user and no arguments.
    '''

    # Create a JSON file with a test user / key.
    user_pwd = 'insecure_ci_password'
    os.mkdir('local_server_work')
    with open('local_server_work/users.json', 'w') as f:
        # Passwords should never be stored in plaintext in a production
        # environment, but the development server is a minimal
        # implementation of the API, intended only for testing.
        f.write(json.dumps({'users': [{
            'username': 'test_user',
            'password': user_pwd,
            'compute_time': 3600,
            'bandwidth': 2**10
        }]}))

    # Start running an sc-server instance.
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local',
                                 '-port', str(unused_tcp_port),
                                 '-auth'])
    time.sleep(10)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost',
                                        'port': unused_tcp_port,
                                        'username': 'test_user',
                                        'password': user_pwd
                                        }))

    monkeypatch.setattr("sys.argv", ['sc-remote', '-credentials', '.test_remote_cfg'])
    retcode = sc_remote.main()

    # Kill the server process.
    srv_proc.kill()

    assert retcode == 0
