from siliconcompiler.apps import sc_ping
import json
import os
import subprocess
import time

###########################
def test_sc_ping(monkeypatch, unused_tcp_port):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
       Use authentication and encryption features.
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

    monkeypatch.setattr("sys.argv", ['sc-ping', '.test_remote_cfg'])
    retcode = sc_ping.main()

    # Kill the server process.
    srv_proc.kill()

    assert retcode == 0
