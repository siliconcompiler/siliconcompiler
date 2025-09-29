import itertools
import json
import os
import pytest
import requests
import sys
import time
import uuid

import os.path

from unittest.mock import patch
from pathlib import Path

from siliconcompiler.utils import default_credentials_file
from siliconcompiler._metadata import default_server

from siliconcompiler.project import Project
from siliconcompiler import Flowgraph
from siliconcompiler.tools.builtin.nop import NOPTask

from siliconcompiler.apps import sc_remote
from siliconcompiler.remote import Client
from siliconcompiler.remote import JobStatus
from siliconcompiler.utils.paths import jobdir


@pytest.fixture(autouse=True)
def patch_home(monkeypatch):
    def new_home():
        return os.getcwd()
    monkeypatch.setattr(Path, 'home', new_home)


@pytest.fixture
def gcd_nop_project(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    project.set_flow(flow)

    project.set('option', 'nodisplay', True)
    project.set('option', 'quiet', True)

    return project


class PausedNOP(NOPTask):
    def task(self):
        return "paused"

    def run(self):
        time.sleep(5)
        return super().run()


###########################
def mock_results(project, node):
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
            'status': JobStatus.COMPLETED
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

    # Create the temporary credentials file, and set the project to use it.
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

    # Create the temporary credentials file, and set the project to use it.
    tmp_creds = scserver_credential(port, user, user_pwd)

    monkeypatch.setattr("sys.argv", ['sc-remote', '-credentials', tmp_creds])
    retcode = sc_remote.main()

    assert retcode == 0


###########################
def test_sc_remote_check_progress(gcd_nop_project, monkeypatch, unused_tcp_port,
                                  scserver_credential):
    '''Test that sc-remote can get info about a running job.
    '''

    def mock_run(self):
        return

    # Mock server responses
    monkeypatch.setattr(requests, 'post', mock_post)
    monkeypatch.setattr(Client, '_run_loop', mock_run)

    # Create the temporary credentials file, and set the project to use it.
    tmp_creds = scserver_credential(unused_tcp_port)

    # Start a small remote job.
    gcd_nop_project.set('option', 'remote', True)
    gcd_nop_project.set('option', 'credentials', tmp_creds)
    gcd_nop_project.set('option', 'nodisplay', True)
    # Start the run, but don't wait for it to finish.
    Client(gcd_nop_project).run()

    # Check job progress.
    monkeypatch.setattr("sys.argv", ['sc-remote',
                                     '-credentials', tmp_creds])
    retcode = sc_remote.main()

    assert retcode == 0


###########################
def test_sc_remote_reconnect(gcd_nop_project, monkeypatch, unused_tcp_port, scserver_credential):
    '''Test that sc-remote can reconnect to a running job.
    '''

    flow = Flowgraph("pausedflow")
    flow.node("stepone", PausedNOP())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    gcd_nop_project.set_flow(flow)

    def mock_run(self):
        return

    # Mock server responses
    monkeypatch.setattr(requests, 'post', mock_post)

    tmp = Client._run_loop
    monkeypatch.setattr(Client, '_run_loop', mock_run)
    monkeypatch.setattr(Client, '_Client__schedule_fetch_result', mock_results)

    # Create the temporary credentials file, and set the project to use it.
    tmp_creds = scserver_credential(unused_tcp_port)

    # Start a small remote job.
    gcd_nop_project.set('option', 'remote', True)
    gcd_nop_project.set('option', 'credentials', tmp_creds)
    gcd_nop_project.set('option', 'nodisplay', True)
    # Start the run, but don't wait for it to finish.
    client = Client(gcd_nop_project)
    client.run()

    monkeypatch.setattr(Client, '_run_loop', tmp)
    # Mock CLI parameters, and the '_finalize_run' call
    # which expects a non-mocked build directory.
    monkeypatch.setattr("sys.argv", ['sc-remote',
                                     '-credentials', tmp_creds,
                                     '-reconnect',
                                     '-cfg', client.remote_manifest()])

    def mock_finalize_run(*args, **kwargs):
        final_manifest = os.path.join(jobdir(gcd_nop_project),
                                      f"{gcd_nop_project.name}.pkg.json")
        with open(final_manifest, 'w') as wf:
            wf.write('{"mocked": "manifest"}')
    monkeypatch.setattr("siliconcompiler.remote.client.Client._finalize_loop", mock_finalize_run)
    # Reconnect to the job.
    with patch("siliconcompiler.project.Project.summary") as summary:
        retcode = sc_remote.main()
        summary.assert_called_once()

    assert retcode == 0
    assert os.path.isfile('mock_result.txt')
    assert os.path.isfile(os.path.join(jobdir(gcd_nop_project),
                                       f"{gcd_nop_project.name}.pkg.json"))


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

    assert generated_creds['address'] == default_server
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

    assert generated_creds['address'] == default_server
    assert 'username' not in generated_creds
    assert 'password' not in generated_creds


def test_configure_default_in_args(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-server',
                                     default_server])

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

    assert generated_creds['address'] == default_server
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
    monkeypatch.setenv("HOME", os.getcwd())
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


@pytest.fixture
def credentials_file(monkeypatch):
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

    return cred_file


def test_configure_update_whitelist(credentials_file, monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-credentials', credentials_file,
                                     '-add', './add_this'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(credentials_file, 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['directory_whitelist'] == [os.path.abspath('add_this')]

    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-credentials', credentials_file,
                                     '-remove', './add_this'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(credentials_file, 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['directory_whitelist'] == []


def test_configure_update_whitelist_multiple(credentials_file, monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-credentials', credentials_file,
                                     '-add', './add_this',
                                     '-add', 'add_this_too'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(credentials_file, 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert set(generated_creds['directory_whitelist']) == \
        set([os.path.abspath('add_this'), os.path.abspath('add_this_too')])

    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-credentials', credentials_file,
                                     '-remove', './add_this',
                                     '-remove', 'add_this_too'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(credentials_file, 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['directory_whitelist'] == []


def test_configure_add_add_whitelist_multiple(credentials_file, monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-credentials', credentials_file,
                                     '-add', './add_this',
                                     '-add', 'add_this_too'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(credentials_file, 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert set(generated_creds['directory_whitelist']) == \
        set([os.path.abspath('add_this'), os.path.abspath('add_this_too')])

    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-credentials', credentials_file,
                                     '-add', './add_this',
                                     '-add', 'add_this_too'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(credentials_file, 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert set(generated_creds['directory_whitelist']) == \
        set([os.path.abspath('add_this'), os.path.abspath('add_this_too')])

    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-credentials', credentials_file,
                                     '-add', './add_this_too_too'])

    sc_remote.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open(credentials_file, 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert set(generated_creds['directory_whitelist']) == \
        set([os.path.abspath('add_this'), os.path.abspath('add_this_too'),
             os.path.abspath('add_this_too_too')])


@pytest.mark.parametrize("args", itertools.permutations(
        ['configure', 'reconnect', 'cancel', 'delete'], r=2))
def test_exclusive_args(args, monkeypatch):

    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     f'-{args[0]}',
                                     f'-{args[1]}'])

    assert sc_remote.main() == 1


@pytest.mark.parametrize("arg", ['reconnect', 'cancel', 'delete'])
def test_require_cfg(arg, monkeypatch):

    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     f'-{arg}'])

    assert sc_remote.main() == 2


def test_configure_list(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-list'])

    with patch("siliconcompiler.remote.client.Client.print_configuration",
               autospec=True) as mock:
        assert sc_remote.main() == 0
        assert mock.called


def test_cancel(monkeypatch, gcd_nop_project):
    gcd_nop_project.write_manifest('test.json')
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-cancel',
                                     '-cfg', 'test.json'])

    with patch("siliconcompiler.remote.client.Client.check",
               autospec=True) as mock_check:
        with patch("siliconcompiler.remote.client.Client.cancel_job",
                   autospec=True) as mock:
            assert sc_remote.main() == 0
            assert mock_check.called
            assert mock.called


def test_delete(monkeypatch, gcd_nop_project):
    gcd_nop_project.write_manifest('test.json')
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-delete',
                                     '-cfg', 'test.json'])

    with patch("siliconcompiler.remote.client.Client.check",
               autospec=True) as mock_check:
        with patch("siliconcompiler.remote.client.Client.delete_job",
                   autospec=True) as mock:
            assert sc_remote.main() == 0
            assert mock_check.called
            assert mock.called


def test_empty_call(monkeypatch, gcd_nop_project):
    gcd_nop_project.write_manifest('test.json')
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-cfg', 'test.json'])

    with patch("siliconcompiler.remote.client.Client.check",
               autospec=True) as mock_check:
        with patch("siliconcompiler.remote.client.Client.check_job_status",
                   autospec=True) as mock0:
            with patch("siliconcompiler.remote.client.Client._report_job_status",
                       autospec=True) as mock1:
                assert sc_remote.main() == 0
                assert mock_check.called
                assert mock0.called
                assert mock1.called
