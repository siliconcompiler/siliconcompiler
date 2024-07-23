from siliconcompiler import Chip
from siliconcompiler.apps import sc_remote
from siliconcompiler.remote import client
from siliconcompiler.remote.server import NodeStatus
import json
import os
import pytest
import requests
import uuid
import sys
from pathlib import Path
from siliconcompiler.utils import default_credentials_file
from siliconcompiler.flowgraph import nodes_to_execute


@pytest.fixture(autouse=True)
def patch_home(monkeypatch):
    def new_home():
        return os.getcwd()
    monkeypatch.setattr(Path, 'home', new_home)


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
            'status': NodeStatus.COMPLETED
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
                'progress_interval': 30
            }
        return build_response(200, json_obj=versions())


###########################
def test_sc_remote_noauth(monkeypatch, scserver, scserver_credential):
    '''Basic sc-remote test: Call with no user credentials and no arguments.
    '''

    # Start running an sc-server instance.
    port = scserver()

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = scserver_credential(port)

    monkeypatch.setattr("sys.argv", ['sc-remote', '-credentials', tmp_creds])
    retcode = sc_remote.main()

    assert retcode == 0


###########################
def test_sc_remote_auth(monkeypatch, scserver, scserver_users, scserver_credential):
    '''Basic sc-remote test: Call with an authenticated user and no arguments.
    '''

    # Create a JSON file with a test user / key.
    user = 'test_user'
    user_pwd = 'insecure_ci_password'
    scserver_users(user, user_pwd)

    port = scserver(auth=True)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = scserver_credential(port, user, user_pwd)

    monkeypatch.setattr("sys.argv", ['sc-remote', '-credentials', tmp_creds])
    retcode = sc_remote.main()

    assert retcode == 0


###########################
@pytest.mark.eda
@pytest.mark.quick
def test_sc_remote_check_progress(monkeypatch, unused_tcp_port, scroot, scserver_credential):
    '''Test that sc-remote can get info about a running job.
    '''

    # Mock server responses
    monkeypatch.setattr(requests, 'post', mock_post)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = scserver_credential(unused_tcp_port)

    # Start a small remote job.
    chip = Chip('gcd')
    chip.input(f"{scroot}/examples/gcd/gcd.v")
    chip.input(f"{scroot}/examples/gcd/gcd.sdc")
    chip.set('option', 'remote', True)
    chip.set('option', 'credentials', tmp_creds)
    chip.set('option', 'nodisplay', True)
    chip.load_target('freepdk45_demo')
    # Start the run, but don't wait for it to finish.
    client._remote_preprocess(chip, nodes_to_execute(chip))
    client._request_remote_run(chip)

    # Check job progress.
    monkeypatch.setattr("sys.argv", ['sc-remote',
                                     '-credentials', tmp_creds])
    retcode = sc_remote.main()

    assert retcode == 0


###########################
@pytest.mark.eda
@pytest.mark.quick
def test_sc_remote_reconnect(monkeypatch, unused_tcp_port, scroot, scserver_credential):
    '''Test that sc-remote can reconnect to a running job.
    '''

    # Mock server responses
    monkeypatch.setattr(requests, 'post', mock_post)
    monkeypatch.setattr(client, 'fetch_results', mock_results)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = scserver_credential(unused_tcp_port)

    # Start a small remote job.
    chip = Chip('gcd')
    chip.input(f"{scroot}/examples/gcd/gcd.v")
    chip.input(f"{scroot}/examples/gcd/gcd.sdc")
    chip.set('option', 'remote', True)
    chip.set('option', 'credentials', tmp_creds)
    chip.set('option', 'nodisplay', True)
    chip.load_target('freepdk45_demo')
    # Start the run, but don't wait for it to finish.
    client._remote_preprocess(chip, nodes_to_execute(chip))
    client._request_remote_run(chip)

    # Mock CLI parameters, and the '_finalize_run' call
    # which expects a non-mocked build directory.
    monkeypatch.setattr("sys.argv", ['sc-remote',
                                     '-credentials', tmp_creds,
                                     '-reconnect',
                                     '-cfg', os.path.join(chip.getworkdir(),
                                                          'import',
                                                          '0',
                                                          'outputs',
                                                          'gcd.pkg.json')])

    def mock_finalize_run(self, environment, status={}):
        final_manifest = os.path.join(chip.getworkdir(), f"{chip.get('design')}.pkg.json")
        with open(final_manifest, 'w') as wf:
            wf.write('{"mocked": "manifest"}')
    monkeypatch.setattr("siliconcompiler.scheduler._finalize_run", mock_finalize_run)
    # Reconnect to the job.
    retcode = sc_remote.main()

    assert retcode == 0
    assert os.path.isfile('mock_result.txt')
    assert os.path.isfile(os.path.join(chip.getworkdir(), f"{chip.get('design')}.pkg.json"))


def test_configure_default(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure'])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
        wf.write('\ny\n')
    with open('cfg_stdin.txt', 'r') as rf:
        sys.stdin = rf

        sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == client.default_server
    assert 'username' not in generated_creds
    assert 'password' not in generated_creds


def test_configure_specify_file(monkeypatch):
    cred_file = 'testing_credentials.json'
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-credentials', cred_file])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
        wf.write('\ny\n')
    with open('cfg_stdin.txt', 'r') as rf:
        sys.stdin = rf

        sc_remote.main()

    assert os.path.exists(cred_file)

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(cred_file, 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == client.default_server
    assert 'username' not in generated_creds
    assert 'password' not in generated_creds


def test_configure_default_in_args(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-server',
                                     client.default_server])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
        wf.write('y\n')
    with open('cfg_stdin.txt', 'r') as rf:
        sys.stdin = rf

        sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == client.default_server
    assert 'username' not in generated_creds
    assert 'password' not in generated_creds


def test_configure_cmdarg(monkeypatch):
    server_name = 'https://example.com'
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-server',
                                     server_name])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
        wf.write('\n\n')
    with open('cfg_stdin.txt', 'r') as rf:
        sys.stdin = rf

        sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == server_name
    assert 'username' not in generated_creds
    assert 'password' not in generated_creds


def test_configure_cmdarg_with_port(monkeypatch):
    server_name = 'https://example.com'
    server_port = 5555
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-server',
                                     f'{server_name}:{server_port}'])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
        wf.write('\n\n')
    with open('cfg_stdin.txt', 'r') as rf:
        sys.stdin = rf

        sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == server_name
    assert generated_creds['port'] == server_port
    assert 'username' not in generated_creds
    assert 'password' not in generated_creds


def test_configure_cmdarg_with_username(monkeypatch):
    username = 'hello'
    password = 'world'
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-server',
                                     f'https://{username}:{password}@example.com'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == 'https://example.com'
    assert generated_creds['username'] == username
    assert generated_creds['password'] == password


def test_configure_cmdarg_no_username_password(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-server',
                                     ':@example.com'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == 'example.com'
    assert 'username' not in generated_creds
    assert 'password' not in generated_creds


def test_configure_interactive(monkeypatch):
    server_name = 'https://example.com'
    username = 'ci_test_user'
    password = 'ci_test_password'
    monkeypatch.setattr('sys.argv', ['sc-remote', '-configure'])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
        wf.write(f'{server_name}\n{username}\n{password}\n')
    with open('cfg_stdin.txt', 'r') as rf:
        sys.stdin = rf

        sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == server_name
    assert generated_creds['username'] == username
    assert generated_creds['password'] == password


def test_configure_override_y(monkeypatch):
    os.makedirs(os.path.dirname(default_credentials_file()))
    with open(default_credentials_file(), 'w') as cf:
        cf.write('{"address": "old_example_address"}')
    os.environ['HOME'] = os.getcwd()
    server_name = 'https://example.com'
    username = 'ci_test_user'
    password = 'ci_test_password'
    monkeypatch.setattr('sys.argv', ['sc-remote', '-configure'])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
        wf.write(f'y\n{server_name}\n{username}\n{password}\n')
    with open('cfg_stdin.txt', 'r') as rf:
        sys.stdin = rf

        sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == server_name
    assert generated_creds['username'] == username
    assert generated_creds['password'] == password


def test_configure_override_n(monkeypatch):
    os.makedirs(os.path.dirname(default_credentials_file()))
    with open(default_credentials_file(), 'w') as cf:
        cf.write('{"address": "old_example_address"}')
    server_name = 'https://example.com'
    username = 'ci_test_user'
    password = 'ci_test_password'
    monkeypatch.setattr('sys.argv', ['sc-remote', '-configure'])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
        wf.write(f'n\n{server_name}\n{username}\n{password}\n')
    with open('cfg_stdin.txt', 'r') as rf:
        sys.stdin = rf

        sc_remote.main()

    # Check that the existing credentials were not overridden.
    generated_creds = {}
    with open(default_credentials_file(), 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] != server_name
    assert 'username' not in generated_creds
    assert 'password' not in generated_creds
