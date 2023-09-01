from siliconcompiler import Chip
from siliconcompiler.apps import sc_remote
from siliconcompiler.remote import client
import json
import os
import pytest
import requests
import subprocess
import time
import uuid


###########################
def mock_results(chip, node):
    '''Mocked 'fetch_results' method which imitates a successful quick job run.
    '''

    with open('mock_result.txt', 'w') as wf:
        wf.write('Job results.\n')


###########################
def mock_post(url, data={}, files={}, stream=True, timeout=0):
    '''Mocked 'post' method which imitates a successful quick job run.
    '''

    def build_response(code, text=None, json_obj=None):
        resp = requests.Response()
        resp.status_code = code

        if text:
            resp.encoding = 'ascii'
            resp._content = bytes(text, encoding=resp.encoding)
        elif json_obj:
            resp.encoding = 'ascii'
            resp._content = bytes(json.dumps(json_obj), encoding=resp.encoding)

        return resp

    if url.endswith('remote_run/'):
        job_hash = uuid.uuid4().hex
        return build_response(200, json_obj={
            'message': f"Starting job: {job_hash}",
            'interval': 30,
            'job_hash': job_hash,
        })
    elif url.endswith('check_progress/'):
        return build_response(200, json_obj={
            'message': 'Job has no running steps.',
            'status': 'completed'
        })
    elif url.endswith('delete_job/'):
        return build_response(200, json_obj={
            'message': 'Job has been deleted.',
            'success': True
        })
    elif url.endswith('check_server/'):
        def versions():
            return {
                'status': 'ready',
                'versions': {'sc': '0', 'sc_schema': '0', 'sc_server': '0'},
            }
        return build_response(200, json_obj=versions())


###########################
@pytest.mark.quick
@pytest.mark.timeout(30)
def test_sc_remote_noauth(monkeypatch, unused_tcp_port):
    '''Basic sc-remote test: Call with no user credentials and no arguments.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local',
                                 '-port', str(unused_tcp_port)])
    time.sleep(20)

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
@pytest.mark.quick
@pytest.mark.timeout(30)
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
    time.sleep(20)

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


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(120)
def test_sc_remote_check_progress(monkeypatch, unused_tcp_port, scroot):
    '''Test that sc-remote can get info about a running job.
    '''

    # Mock server responses
    monkeypatch.setattr(requests, 'post', mock_post)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    remote_cfg = {'address': 'localhost', 'port': unused_tcp_port}
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps(remote_cfg))

    # Start a small remote job.
    chip = Chip('gcd')
    chip.input(f"{scroot}/examples/gcd/gcd.v")
    chip.input(f"{scroot}/examples/gcd/gcd.sdc")
    chip.set('option', 'remote', True)
    chip.set('option', 'credentials', tmp_creds)
    chip.set('option', 'nodisplay', True)
    chip.load_target('freepdk45_demo')
    chip.status['remote_cfg'] = remote_cfg
    # Start the run, but don't wait for it to finish.
    client._remote_preprocess(chip, chip.list_steps())
    client._request_remote_run(chip)

    # Check job progress.
    monkeypatch.setattr("sys.argv", ['sc-remote',
                                     '-credentials', '.test_remote_cfg'])
    retcode = sc_remote.main()

    assert retcode == 0


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(120)
def test_sc_remote_reconnect(monkeypatch, unused_tcp_port, scroot):
    '''Test that sc-remote can reconnect to a running job.
    '''

    # Mock server responses
    monkeypatch.setattr(requests, 'post', mock_post)
    monkeypatch.setattr(client, 'fetch_results', mock_results)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    remote_cfg = {'address': 'localhost', 'port': unused_tcp_port}
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps(remote_cfg))

    # Start a small remote job.
    chip = Chip('gcd')
    chip.input(f"{scroot}/examples/gcd/gcd.v")
    chip.input(f"{scroot}/examples/gcd/gcd.sdc")
    chip.set('option', 'remote', True)
    chip.set('option', 'credentials', tmp_creds)
    chip.set('option', 'nodisplay', True)
    chip.load_target('freepdk45_demo')
    chip.status['remote_cfg'] = remote_cfg
    # Start the run, but don't wait for it to finish.
    client._remote_preprocess(chip, chip.list_steps())
    client._request_remote_run(chip)

    # Mock CLI parameters, and the '_finalize_run' call
    # which expects a non-mocked build directory.
    monkeypatch.setattr("sys.argv", ['sc-remote',
                                     '-credentials', '.test_remote_cfg',
                                     '-reconnect',
                                     '-cfg', os.path.join(chip._getworkdir(),
                                                          'import',
                                                          '0',
                                                          'outputs',
                                                          'gcd.pkg.json')])

    def mock_finalize_run(self, steplist, environment, status={}):
        final_manifest = os.path.join(chip._getworkdir(), f"{chip.get('design')}.pkg.json")
        with open(final_manifest, 'w') as wf:
            wf.write('{"mocked": "manifest"}')
    monkeypatch.setattr("siliconcompiler.Chip._finalize_run", mock_finalize_run)
    # Reconnect to the job.
    retcode = sc_remote.main()

    assert retcode == 0
    assert os.path.isfile('mock_result.txt')
    assert os.path.isfile(os.path.join(chip._getworkdir(), f"{chip.get('design')}.pkg.json"))
