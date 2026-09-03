import pytest
import json
import os
import requests
import sys
import tarfile
import tempfile
import time

import os.path

from aiohttp import web
from unittest.mock import Mock, AsyncMock, patch
from siliconcompiler import NodeStatus
from siliconcompiler.remote.server import Server
from siliconcompiler.remote import JobStatus, NodeStatus as RemoteNodeStatus


def _job_owner(nfs_path):
    '''Reads the owner record off the one job in a server's mount.'''
    jobs = [entry for entry in os.listdir(nfs_path) if len(entry) == 32]
    assert len(jobs) == 1, f"expected one job in {nfs_path}, found {jobs}"
    with open(os.path.join(nfs_path, jobs[0], '.owner')) as f:
        return json.load(f)


###########################
@pytest.mark.timeout(60)
def test_server_authenticated(gcd_nop_project, scserver, scserver_users, scserver_credential,
                              scserver_nfs_path):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
       Use authentication and encryption features.
    '''

    # Create a JSON file with a test user / key.
    user = 'test_user'
    user_pwd = 'insecure_ci_password'
    scserver_users(user, user_pwd)

    # Start running an sc-server instance.
    port = scserver(auth=True)

    # Create the temporary credentials file, and set the project to use it.
    scserver_credential(port, user, user_pwd, project=gcd_nop_project)

    gcd_nop_project.set('option', 'nodisplay', True)

    # Run remote build.
    assert gcd_nop_project.run()

    # Verify that GDS file was generated and returned.
    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')

    assert gcd_nop_project.history("job0").get("record", "status", step="stepone", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS

    # The submitter is recorded on the job, which is what a later delete is checked
    # against. Asserted on a real submission because a check against a record that
    # nothing writes would pass every unit test and authorize everyone.
    assert _job_owner(scserver_nfs_path) == {'username': user}


###########################
@pytest.mark.timeout(60)
def test_server_not_authenticated(gcd_nop_project, scserver, scserver_users,
                                  scserver_credential):
    '''Basic sc-server test: Run a local instance of a server, and attempt to
       authenticate a user with an invalid key. The remote run should fail.
    '''

    # Create a JSON file with a test user / key.
    # This key is random, so it shouldn't match the stored test keypair.
    user = 'test_user'
    user_pwd = 'insecure_ci_password'
    scserver_users(user, user_pwd)

    # Start running an sc-server instance.
    port = scserver(auth=True)

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    gcd_nop_project.set('option', 'nodisplay', True)

    # Create the temporary credentials file, and set the project to use it.
    tmp_creds = scserver_credential(port, user, user_pwd + '1')

    # Add remote parameters.
    gcd_nop_project.set('option', 'remote', True)
    gcd_nop_project.set('option', 'credentials', tmp_creds)

    # Run remote build. It should fail, so catch the expected exception.
    with pytest.raises(RuntimeError,
                       match=r"^Run failed: Server responded with 403: Authentication error\.$"):
        gcd_nop_project.run()


@pytest.mark.timeout(60)
def test_server(gcd_remote_test, scserver_nfs_path):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Get the partially-configured GCD project object from the fixture.
    gcd_project = gcd_remote_test()

    # Run the remote job.
    assert gcd_project.run()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')

    assert gcd_project.history("job0").get("record", "status", step="stepone", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS

    # Without authentication there is no identity to record, and an unowned job is
    # one anybody holding the hash may delete.
    assert _job_owner(scserver_nfs_path) == {'username': None}


###########################
@pytest.mark.timeout(60)
def test_server_partial(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test runs a partial flowgraph on the remote server.
    '''

    # Get the partially-configured GCD project object from the fixture.
    gcd_project = gcd_remote_test()

    # Set from/to to limit how many steps are run on the remote host.
    gcd_project.set('option', 'to', ['stepone'])

    # Run the remote job.
    assert gcd_project.run()

    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert not os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')

    assert gcd_project.history("job0").get("record", "status", step="stepone", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.PENDING


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.slurm
@pytest.mark.timeout(300)
def test_server_slurm(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Get the partially-configured GCD project object from the fixture.
    gcd_project = gcd_remote_test(use_slurm=True)

    # Run the remote job.
    gcd_project.run()

    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')

    assert gcd_project.history("job0").get("record", "status", step="stepone", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS


###########################
# Unit tests for Server class
###########################

def test_server_init():
    '''Test Server initialization'''
    server = Server()

    # Check that logger is initialized
    assert server.logger is not None
    assert server.logger.name.startswith('sc_server_')

    # Check that locks and dicts are initialized
    assert server.sc_jobs_lock is not None
    assert isinstance(server.sc_jobs, dict)
    assert isinstance(server.sc_project_lookup, dict)
    assert len(server.sc_jobs) == 0
    assert len(server.sc_project_lookup) == 0


def test_server_nfs_mount_property():
    '''Test nfs_mount property returns absolute path'''
    server = Server()
    server.set('option', 'nfsmount', 'relative/path')

    # Should return absolute path
    result = server.nfs_mount
    assert result == os.path.abspath('relative/path')


def test_server_checkinterval_property():
    '''Test checkinterval property'''
    server = Server()

    # Get default value
    interval = server.checkinterval
    assert isinstance(interval, (int, float))

    # Set and verify
    server.set('option', 'checkinterval', 5)
    assert server.checkinterval == 5


def test_server_job_name():
    '''Test job_name method'''
    server = Server()

    # Test with username
    result = server.job_name('testuser', 'abc123')
    assert result == 'testuser_abc123'

    # Test without username (None)
    result = server.job_name(None, 'abc123')
    assert result == 'abc123'

    # Test with empty string username
    result = server.job_name('', 'abc123')
    assert result == 'abc123'


def test_server_response():
    '''Test __response private method'''
    server = Server()

    # Test default status
    response = server._Server__response('Test message')
    assert response.status == 200
    assert isinstance(response, web.Response)

    # Test custom status
    response = server._Server__response('Error message', status=404)
    assert response.status == 404


def test_server_auth_password():
    '''Test __auth_password method'''
    server = Server()

    # Setup user keys
    server.user_keys = {
        'user1': {'password': 'pass123', 'compute_time': 0, 'bandwidth': 0},
        'user2': {'password': 'secret456', 'compute_time': 100, 'bandwidth': 50}
    }

    # Test successful authentication
    assert server._Server__auth_password('user1', 'pass123') is True
    assert server._Server__auth_password('user2', 'secret456') is True

    # Test failed authentication - wrong password
    assert server._Server__auth_password('user1', 'wrong') is False
    assert server._Server__auth_password('user2', 'wrong') is False

    # Test failed authentication - unknown user
    assert server._Server__auth_password('unknown', 'pass123') is False


@pytest.mark.asyncio
async def test_handle_check_server_basic():
    '''Test handle_check_server endpoint without authentication'''
    server = Server()
    server.set('option', 'auth', False)
    server.set('option', 'checkinterval', 10)

    # Create mock request with empty dict (no username/key)
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={})

    # Call handler
    response = await server.handle_check_server(mock_request)

    # Verify response
    assert response.status == 200
    data = json.loads(response.body)
    from siliconcompiler._metadata import detailed_version as sc_version
    from siliconcompiler.schema import __version__ as sc_schema_version
    from siliconcompiler.remote.server import Server as ServerClass
    assert data == {
        'status': 'ready',
        'versions': {
            'sc': sc_version,
            'sc_schema': sc_schema_version,
            'sc_server': ServerClass.__version__,
        },
        'progress_interval': 10
    }


@pytest.mark.asyncio
async def test_handle_check_server_with_user():
    '''Test handle_check_server endpoint with user info'''
    server = Server()
    server.set('option', 'auth', False)
    server.set('option', 'checkinterval', 5)

    # Setup user keys
    server.user_keys = {
        'testuser': {'password': 'pass', 'compute_time': 100, 'bandwidth': 200}
    }

    # Create mock request with both username and key (required by schema)
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'username': 'testuser', 'key': 'pass'})

    # Call handler
    response = await server.handle_check_server(mock_request)

    # Verify response includes user info
    assert response.status == 200
    data = json.loads(response.body)
    from siliconcompiler._metadata import detailed_version as sc_version
    from siliconcompiler.schema import __version__ as sc_schema_version
    from siliconcompiler.remote.server import Server as ServerClass
    assert data == {
        'status': 'ready',
        'versions': {
            'sc': sc_version,
            'sc_schema': sc_schema_version,
            'sc_server': ServerClass.__version__,
        },
        'progress_interval': 5,
        'user_info': {
            'compute_time': 100,
            'bandwidth_kb': 200
        }
    }


@pytest.mark.asyncio
async def test_handle_check_progress_running():
    '''Test handle_check_progress when job is running'''
    server = Server()
    server.set('option', 'auth', False)

    # Setup a running job
    server.sc_jobs = {
        'testuser_12345678901234567890123456789012': {
            'step0': {'status': RemoteNodeStatus.RUNNING},
            'step1': {'status': RemoteNodeStatus.PENDING}
        }
    }

    # Create mock request with valid job_hash (32 hex chars) and job_id
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={
        'username': 'testuser',
        'key': 'pass',
        'job_hash': '12345678901234567890123456789012',
        'job_id': '1'
    })

    # Call handler
    response = await server.handle_check_progress(mock_request)

    # Verify response
    assert response.status == 200
    data = json.loads(response.body)
    assert data == {
        'status': JobStatus.RUNNING,
        'message': server.sc_jobs['testuser_12345678901234567890123456789012']
    }


@pytest.mark.asyncio
async def test_handle_check_progress_completed():
    '''Test handle_check_progress when job is completed'''
    server = Server()
    server.set('option', 'auth', False)

    # No running jobs
    server.sc_jobs = {}

    # Create mock request with valid job_hash (32 hex chars) and job_id
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={
        'job_hash': '12345678901234567890123456789012',
        'job_id': '1'
    })

    # Call handler
    response = await server.handle_check_progress(mock_request)

    # Verify response
    assert response.status == 200
    data = json.loads(response.body)
    assert data == {
        'status': JobStatus.COMPLETED,
        'message': 'Job has no running steps.'
    }


@pytest.mark.asyncio
async def test_handle_get_results_not_found():
    '''Test handle_get_results when results don't exist'''
    server = Server()
    server.set('option', 'auth', False)
    server.set('option', 'nfsmount', tempfile.mkdtemp())

    # Create mock request
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={})
    # Use valid 32-char hex job_hash
    mock_request.match_info = {'job_hash': '00000000000000000000000000000000'}

    # Call handler
    response = await server.handle_get_results(mock_request)

    # Verify response
    assert response.status == 404
    data = json.loads(response.body)
    assert data == {
        'message': 'Could not find results for the requested job/node.'
    }


@pytest.mark.asyncio
async def test_handle_get_results_with_node():
    '''Test handle_get_results with specific node'''
    server = Server()
    server.set('option', 'auth', False)

    # Create temporary directory and file
    tmpdir = tempfile.mkdtemp()
    server.set('option', 'nfsmount', tmpdir)

    # Use valid 32-char hex job_hash
    job_hash = 'fedcba98765432100123456789abcdef'
    node = 'step0'
    job_dir = os.path.join(tmpdir, job_hash)
    os.makedirs(job_dir, exist_ok=True)

    # Create a dummy tar.gz file
    tar_path = os.path.join(job_dir, f'{job_hash}_{node}.tar.gz')
    with tarfile.open(tar_path, 'w:gz') as tar:
        # Add a dummy file
        info = tarfile.TarInfo(name='test.txt')
        info.size = 0
        tar.addfile(info)

    # Create mock request
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'node': node})
    mock_request.match_info = {'job_hash': job_hash}

    # Call handler
    response = await server.handle_get_results(mock_request)

    # Verify response
    assert isinstance(response, web.FileResponse)


@pytest.mark.asyncio
async def test_handle_delete_job_running():
    '''Test handle_delete_job when job is still running'''
    server = Server()
    server.set('option', 'auth', False)

    # Setup a running job with valid 32-char hex job_hash
    job_hash = '12345678901234567890123456789012'
    server.sc_jobs = {
        f'job_with_{job_hash}_in_name': {'status': RemoteNodeStatus.RUNNING}
    }

    # Create mock request
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash})

    # Call handler
    response = await server.handle_delete_job(mock_request)

    # Verify error response
    assert response.status == 400
    data = json.loads(response.body)
    assert data == {
        'message': 'Error: job is still running.',
        'success': False
    }


@pytest.mark.asyncio
async def test_handle_delete_job_success():
    '''Test handle_delete_job successful deletion'''
    server = Server()
    server.set('option', 'auth', False)

    # Create temporary directory structure
    tmpdir = tempfile.mkdtemp()
    server.set('option', 'nfsmount', tmpdir)

    # Use valid 32-char hex job_hash
    job_hash = 'abcdef01234567890abcdef012345678'
    job_dir = os.path.join(tmpdir, job_hash)
    os.makedirs(job_dir, exist_ok=True)

    # Create a dummy file
    with open(os.path.join(job_dir, 'test.txt'), 'w') as f:
        f.write('test')

    # Create tar file
    tar_file = f'{job_dir}.tar.gz'
    with tarfile.open(tar_file, 'w:gz') as tar:
        tar.add(job_dir, arcname='.')

    # No running jobs
    server.sc_jobs = {}

    # Verify files exist before deletion
    assert os.path.exists(job_dir)
    assert os.path.exists(tar_file)

    # Create mock request
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash})

    # Call handler
    response = await server.handle_delete_job(mock_request)

    # Verify successful deletion
    assert response.status == 200
    assert json.loads(response.body) == {
        'message': 'Job deleted.',
        'success': True
    }
    assert not os.path.exists(job_dir)
    assert not os.path.exists(tar_file)


def _owned_job(server, job_hash, username):
    """Lays down a job directory carrying the owner record the server writes."""
    job_dir = os.path.join(server.nfs_mount, job_hash)
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, '.owner'), 'w') as f:
        json.dump({'username': username}, f)
    return job_dir


async def _delete(server, job_hash, username=None):
    params = {'job_hash': job_hash}
    if username:
        params['username'] = username
        params['key'] = 'pass'
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value=params)
    return await server.handle_delete_job(mock_request)


@pytest.mark.asyncio
async def test_handle_delete_job_wrong_user():
    '''A job that belongs to somebody else is not deletable by a valid hash alone'''
    server = Server()
    server.set('option', 'auth', True)
    server.set('option', 'nfsmount', tempfile.mkdtemp())
    server.user_keys = {'owner': {'password': 'pass'}, 'stranger': {'password': 'pass'}}
    server.sc_jobs = {}

    job_hash = 'abcdef01234567890abcdef012345678'
    job_dir = _owned_job(server, job_hash, 'owner')

    response = await _delete(server, job_hash, username='stranger')

    assert response.status == 403
    assert json.loads(response.body) == {
        'message': 'Error: job belongs to another user.',
        'success': False
    }
    assert os.path.exists(job_dir), "the job was deleted anyway"


@pytest.mark.asyncio
async def test_handle_delete_job_owner():
    '''The user who submitted the job can delete it'''
    server = Server()
    server.set('option', 'auth', True)
    server.set('option', 'nfsmount', tempfile.mkdtemp())
    server.user_keys = {'owner': {'password': 'pass'}}
    server.sc_jobs = {}

    job_hash = 'abcdef01234567890abcdef012345678'
    job_dir = _owned_job(server, job_hash, 'owner')

    response = await _delete(server, job_hash, username='owner')

    assert response.status == 200
    assert json.loads(response.body) == {'message': 'Job deleted.', 'success': True}
    assert not os.path.exists(job_dir)


@pytest.mark.asyncio
async def test_handle_delete_job_unowned_is_open():
    '''A job submitted without authentication has no owner, so anyone may delete it.

    That is this reference server's documented behaviour on an unauthenticated
    server, not a gap: with no identity on the request there is nothing to check.
    '''
    server = Server()
    server.set('option', 'auth', False)
    server.set('option', 'nfsmount', tempfile.mkdtemp())
    server.sc_jobs = {}

    job_hash = 'abcdef01234567890abcdef012345678'
    job_dir = _owned_job(server, job_hash, None)

    response = await _delete(server, job_hash)

    assert response.status == 200
    assert not os.path.exists(job_dir)


@pytest.mark.asyncio
async def test_handle_delete_job_malformed_owner_record():
    """A record this server did not write says nothing about who owns the job,
    which is not the same as saying nobody does."""
    server = Server()
    server.set('option', 'auth', False)
    server.set('option', 'nfsmount', tempfile.mkdtemp())
    server.sc_jobs = {}

    job_hash = 'abcdef01234567890abcdef012345678'
    job_dir = os.path.join(server.nfs_mount, job_hash)
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, '.owner'), 'w') as f:
        json.dump({}, f)

    response = await _delete(server, job_hash)

    assert response.status == 403
    assert os.path.exists(job_dir), "a job with an unreadable owner was deleted"


@pytest.mark.asyncio
async def test_handle_delete_job_without_owner_record():
    '''A job predating the owner record has no owner to enforce'''
    server = Server()
    server.set('option', 'auth', False)
    server.set('option', 'nfsmount', tempfile.mkdtemp())
    server.sc_jobs = {}

    job_hash = 'abcdef01234567890abcdef012345678'
    job_dir = os.path.join(server.nfs_mount, job_hash)
    os.makedirs(job_dir, exist_ok=True)

    response = await _delete(server, job_hash)

    assert response.status == 200
    assert not os.path.exists(job_dir)


@pytest.mark.asyncio
async def test_check_request_invalid_json():
    '''Test _check_request with invalid JSON schema'''
    server = Server()
    server.set('option', 'auth', False)

    # Create a simple validator that requires a 'test' field
    def mock_validator(data):
        if 'required_field' not in data:
            from fastjsonschema import JsonSchemaException
            raise JsonSchemaException('Missing required field')
        return data

    # Test with invalid request
    params, response = server._check_request({'invalid': 'data'}, mock_validator)

    # Verify error response
    assert response is not None
    assert response.status == 400
    assert params == {}


@pytest.mark.asyncio
async def test_check_request_missing_auth():
    '''Test _check_request with missing authentication'''
    server = Server()
    server.set('option', 'auth', True)

    # Create a passthrough validator
    def mock_validator(data):
        return data

    # Test with missing auth
    params, response = server._check_request({'some': 'data'}, mock_validator)

    # Verify error response
    assert response is not None
    assert response.status == 400
    data = json.loads(response.body)
    assert data == {
        'message': 'Error: some authentication parameters are missing.'
    }


@pytest.mark.asyncio
async def test_check_request_invalid_auth():
    '''Test _check_request with invalid authentication'''
    server = Server()
    server.set('option', 'auth', True)

    # Setup user keys
    server.user_keys = {
        'testuser': {'password': 'correct_pass', 'compute_time': 0, 'bandwidth': 0}
    }

    # Create a passthrough validator
    def mock_validator(data):
        return data

    # Test with wrong password
    params, response = server._check_request({
        'username': 'testuser',
        'key': 'wrong_pass'
    }, mock_validator)

    # Verify error response
    assert response is not None
    assert response.status == 403
    data = json.loads(response.body)
    assert data == {
        'message': 'Authentication error.'
    }


@pytest.mark.asyncio
async def test_check_request_valid_auth():
    '''Test _check_request with valid authentication'''
    server = Server()
    server.set('option', 'auth', True)

    # Setup user keys
    server.user_keys = {
        'testuser': {'password': 'correct_pass', 'compute_time': 0, 'bandwidth': 0}
    }

    # Create a passthrough validator
    def mock_validator(data):
        return data

    # Test with correct credentials
    params, response = server._check_request({
        'username': 'testuser',
        'key': 'correct_pass',
        'other': 'data'
    }, mock_validator)

    # Verify success
    assert response is None
    assert params == {
        'username': 'testuser',
        'key': 'correct_pass',
        'other': 'data'
    }


@pytest.mark.asyncio
async def test_check_request_no_auth_adds_username():
    '''Test _check_request adds username None when auth disabled'''
    server = Server()
    server.set('option', 'auth', False)

    # Create a passthrough validator
    def mock_validator(data):
        return data

    # Test without username in request
    params, response = server._check_request({'some': 'data'}, mock_validator)

    # Verify username is added as None
    assert response is None
    assert params == {
        'some': 'data',
        'username': None
    }


def test_handle_get_results_none_node():
    '''Test handle_get_results with node=None'''
    import asyncio

    async def async_test():
        server = Server()
        server.set('option', 'auth', False)

        # Create temporary directory and file
        tmpdir = tempfile.mkdtemp()
        server.set('option', 'nfsmount', tmpdir)

        # Use valid 32-char hex job_hash
        job_hash = 'fedcba98765432100123456789abcdef'
        job_dir = os.path.join(tmpdir, job_hash)
        os.makedirs(job_dir, exist_ok=True)

        # Create a dummy tar.gz file for None node
        tar_path = os.path.join(job_dir, f'{job_hash}_None.tar.gz')
        with tarfile.open(tar_path, 'w:gz') as tar:
            # Add a dummy file
            info = tarfile.TarInfo(name='test.txt')
            info.size = 0
            tar.addfile(info)

        # Create mock request without node (should default to None)
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={})
        mock_request.match_info = {'job_hash': job_hash}

        # Call handler
        response = await server.handle_get_results(mock_request)

        # Verify response
        assert isinstance(response, web.FileResponse)

    asyncio.run(async_test())


def test_handle_delete_job_not_found():
    '''A job that was never there is the 404 the response schema documents'''
    import asyncio

    async def async_test():
        server = Server()
        server.set('option', 'auth', False)

        # Create temporary directory structure
        tmpdir = tempfile.mkdtemp()
        server.set('option', 'nfsmount', tmpdir)

        # Use valid 32-char hex job_hash that doesn't exist
        job_hash = 'abcdef01234567890abcdef012345678'

        # No running jobs
        server.sc_jobs = {}

        # Create mock request
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={'job_hash': job_hash})

        response = await server.handle_delete_job(mock_request)

        assert response.status == 404
        assert json.loads(response.body) == {
            'message': 'Job does not exist.',
            'success': False
        }

    asyncio.run(async_test())


def test_check_request_valid_without_username():
    '''Test _check_request with valid request but no username field'''
    server = Server()
    server.set('option', 'auth', False)

    # Create a passthrough validator
    def mock_validator(data):
        return data

    # Test with request containing data but no username
    params, response = server._check_request({'job_hash': 'test123'}, mock_validator)

    # Verify username is added as None
    assert response is None
    assert params == {
        'job_hash': 'test123',
        'username': None
    }


def test_check_request_empty():
    '''Test _check_request with empty request'''
    server = Server()
    server.set('option', 'auth', False)

    # Create a validator that accepts empty dict
    def mock_validator(data):
        return data

    # Test with empty request
    params, response = server._check_request({}, mock_validator)

    # Verify username is added as None
    assert response is None
    assert params == {
        'username': None
    }


def test_handle_check_progress_without_auth():
    '''Test handle_check_progress without username/key'''
    import asyncio

    async def async_test():
        server = Server()
        server.set('option', 'auth', False)

        # No running jobs
        server.sc_jobs = {}

        # Create mock request without username/key
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={
            'job_hash': '12345678901234567890123456789012',
            'job_id': '1'
        })

        # Call handler
        response = await server.handle_check_progress(mock_request)

        # Verify response
        assert response.status == 200
        data = json.loads(response.body)
        assert data == {
            'status': JobStatus.COMPLETED,
            'message': 'Job has no running steps.'
        }

    asyncio.run(async_test())


def test_handle_check_server_schema_error():
    '''Test handle_check_server with invalid schema (username without key)'''
    import asyncio

    async def async_test():
        server = Server()
        server.set('option', 'auth', False)

        # Create mock request with only username (missing key - violates schema dependency)
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={'username': 'testuser'})

        # Call handler
        response = await server.handle_check_server(mock_request)

        # Verify error response due to schema violation
        assert response.status == 400

    asyncio.run(async_test())


def test_handle_check_progress_invalid_job_hash():
    '''Test handle_check_progress with invalid job_hash format'''
    import asyncio

    async def async_test():
        server = Server()
        server.set('option', 'auth', False)

        # Create mock request with invalid job_hash (not 32 hex chars)
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={
            'job_hash': 'invalid',
            'job_id': '1'
        })

        # Call handler
        response = await server.handle_check_progress(mock_request)

        # Verify error response due to schema violation
        assert response.status == 400

    asyncio.run(async_test())


def test_handle_delete_job_invalid_hash():
    '''Test handle_delete_job with invalid job_hash format'''
    import asyncio

    async def async_test():
        server = Server()
        server.set('option', 'auth', False)

        # Create mock request with invalid job_hash
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={'job_hash': 'bad_hash'})

        # Call handler
        response = await server.handle_delete_job(mock_request)

        # Verify error response due to schema violation
        assert response.status == 400

    asyncio.run(async_test())


def test_handle_get_results_invalid_job_hash():
    '''Test handle_get_results with invalid job_hash in URL'''
    import asyncio

    async def async_test():
        server = Server()
        server.set('option', 'auth', False)
        server.set('option', 'nfsmount', tempfile.mkdtemp())

        # Create mock request with invalid job_hash in URL
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={})
        mock_request.match_info = {'job_hash': 'invalid_hash'}

        # Call handler - should fail validation
        response = await server.handle_get_results(mock_request)

        # Verify it is rejected rather than looked for
        assert response.status == 400

    asyncio.run(async_test())


def test_server_run_nfs_creation():
    '''Test that run creates nfs_mount directory if it doesn't exist'''
    server = Server()

    # Create a temporary directory that we'll delete
    tmpdir = tempfile.mkdtemp()
    test_mount = os.path.join(tmpdir, 'test_nfs')
    server.set('option', 'nfsmount', test_mount)
    server.set('option', 'auth', False)

    # Verify directory doesn't exist
    assert not os.path.exists(test_mount)

    with patch("aiohttp.web.run_app") as mock_run_app:
        server.run()
        mock_run_app.assert_called_once()

    # Verify directory doesn't exist
    assert os.path.exists(test_mount)


def test_server_run_creates_gitignore():
    '''run() keeps the mount out of git'''
    server = _make_server()

    with patch("aiohttp.web.run_app"):
        server.run()

    gitignore = os.path.join(server.nfs_mount, ".gitignore")
    assert os.path.isfile(gitignore)
    with open(gitignore) as f:
        assert f.read() == "*"


def test_remote_sc_basic_setup():
    '''Test remote_sc method basic setup'''
    from siliconcompiler import Project, Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask
    from siliconcompiler import NodeStatus as SCNodeStatus

    server = Server()
    tmpdir = tempfile.mkdtemp()
    server.set('option', 'nfsmount', tmpdir)
    server.set('option', 'cluster', 'local')

    # Create a test project
    project = Project('test_remote')
    project.set('option', 'builddir', tmpdir)
    project.set('record', 'remoteid', 'test_hash_remote')

    # Create a simple flow
    flow = Flowgraph("testflow")
    flow.node("step1", NOPTask())
    project.set_flow(flow)
    project.set('option', 'flow', 'testflow')

    # Test that we can set up the job structure like remote_sc does
    job_hash = project.get('record', 'remoteid')
    username = 'testuser'

    # Build nodes structure like remote_sc
    from siliconcompiler.flowgraph import RuntimeFlowgraph
    runtime = RuntimeFlowgraph(
        project.get("flowgraph", project.get('option', 'flow'), field='schema'),
        from_steps=project.get('option', 'from'),
        to_steps=project.get('option', 'to'),
        prune_nodes=project.get('option', 'prune'))

    nodes = {}
    nodes[None] = {"status": SCNodeStatus.PENDING}
    for step, index in runtime.get_nodes():
        status = project.get('record', 'status', step=step, index=index)
        if not status:
            status = SCNodeStatus.PENDING
        nodes[f"{step}{index}"] = {"status": status}

    # Verify nodes were created
    assert None in nodes
    assert 'step10' in nodes

    # Verify job_name works
    sc_job_name = server.job_name(username, job_hash)
    assert sc_job_name == f'{username}_{job_hash}'


def test_handle_remote_run_missing_manifest():
    '''Test handle_remote_run with missing manifest in params'''
    import asyncio

    async def async_test():
        server = Server()
        server.set('option', 'auth', False)
        tmpdir = tempfile.mkdtemp()
        server.set('option', 'nfsmount', tmpdir)

        # Create a mock multipart reader
        class MockPart:
            def __init__(self, name, data):
                self.name = name
                self._data = data

            async def json(self):
                return self._data

            async def read_chunk(self):
                return None

        class MockMultipartReader:
            def __init__(self):
                self.parts = [
                    MockPart('params', {'params': {}})  # Missing 'cfg'
                ]
                self.index = 0

            async def next(self):
                if self.index < len(self.parts):
                    part = self.parts[self.index]
                    self.index += 1
                    return part
                return None

        # Create mock request
        mock_request = Mock()

        # Make multipart() return an awaitable
        async def get_multipart():
            return MockMultipartReader()
        mock_request.multipart = get_multipart

        # Call handler
        response = await server.handle_remote_run(mock_request)

        # Verify error response
        assert response.status == 400
        data = json.loads(response.body)
        assert 'Manifest not provided' in data['message']

    asyncio.run(async_test())


@pytest.mark.asyncio
async def test_handle_get_results_with_auth_error():
    '''Test handle_get_results with authentication error'''
    server = Server()
    server.set('option', 'auth', True)
    server.set('option', 'nfsmount', tempfile.mkdtemp())

    # Setup user keys
    server.user_keys = {
        'testuser': {'password': 'correct_pass', 'compute_time': 0, 'bandwidth': 0}
    }

    # Create mock request with wrong password
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={
        'username': 'testuser',
        'key': 'wrong_password'
    })
    mock_request.match_info = {'job_hash': '00000000000000000000000000000000'}

    # Call handler
    response = await server.handle_get_results(mock_request)

    # Verify authentication error
    assert response.status == 403


###########################
# Job tracking helpers
###########################

def _make_server(cluster='local', auth=False):
    '''Server with a working nfs mount, ready to have handlers called on it.'''
    server = Server()
    server.set('option', 'auth', auth)
    server.set('option', 'cluster', cluster)
    server.set('option', 'nfsmount', tempfile.mkdtemp())
    return server


def _register_job(server, job_hash, nodes=None, username=None):
    '''Register a running job the way remote_sc() does.'''
    if nodes is None:
        nodes = {'stepone0': {'status': NodeStatus.RUNNING,
                              'step': 'stepone', 'index': '0'}}
    job_name = server.job_name(username, job_hash)
    server.sc_jobs[job_name] = {None: {'status': NodeStatus.SUCCESS}, **nodes}
    return job_name


###########################
# job ownership, across every handler that names a job
###########################

def _authed_server_with_job(job_hash, owner):
    """A server with one job owned by `owner`, and two users who can authenticate."""
    server = _make_server(auth=True)
    server.user_keys = {'owner': {'password': 'pass'}, 'stranger': {'password': 'pass'}}
    job_dir = os.path.join(server.nfs_mount, job_hash)
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, '.owner'), 'w') as f:
        json.dump({'username': owner}, f)
    return server, job_dir


@pytest.mark.asyncio
async def test_handle_get_results_wrong_user():
    """Authenticating says nothing about whose results these are."""
    job_hash = 'fedcba98765432100123456789abcdef'
    server, job_dir = _authed_server_with_job(job_hash, 'owner')

    node = 'step0'
    tar_path = os.path.join(job_dir, f'{job_hash}_{node}.tar.gz')
    with tarfile.open(tar_path, 'w:gz') as tar:
        info = tarfile.TarInfo(name='test.txt')
        info.size = 0
        tar.addfile(info)

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'node': node,
                                                'username': 'stranger', 'key': 'pass'})
    mock_request.match_info = {'job_hash': job_hash}

    response = await server.handle_get_results(mock_request)

    assert response.status == 403
    assert not isinstance(response, web.FileResponse), "another user's results were served"
    assert json.loads(response.body) == {'message': 'Error: job belongs to another user.'}


@pytest.mark.asyncio
async def test_handle_get_results_owner():
    """The owner still gets their results."""
    job_hash = 'fedcba98765432100123456789abcdef'
    server, job_dir = _authed_server_with_job(job_hash, 'owner')

    node = 'step0'
    with tarfile.open(os.path.join(job_dir, f'{job_hash}_{node}.tar.gz'), 'w:gz') as tar:
        info = tarfile.TarInfo(name='test.txt')
        info.size = 0
        tar.addfile(info)

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'node': node,
                                                'username': 'owner', 'key': 'pass'})
    mock_request.match_info = {'job_hash': job_hash}

    response = await server.handle_get_results(mock_request)

    assert isinstance(response, web.FileResponse)


@pytest.mark.asyncio
async def test_handle_cancel_job_wrong_user():
    """A stranger's cancel is refused rather than quietly missing the job."""
    job_hash = 'a' * 32
    server, _ = _authed_server_with_job(job_hash, 'owner')
    _register_job(server, job_hash, username='owner')

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash,
                                                'username': 'stranger', 'key': 'pass'})

    response = await server.handle_cancel_job(mock_request)

    assert response.status == 403
    assert json.loads(response.body) == {'message': 'Error: job belongs to another user.',
                                         'success': False}
    assert server.sc_canceled_jobs == set(), "another user's job was canceled"


@pytest.mark.asyncio
async def test_handle_check_progress_wrong_user():
    """A stranger polling is refused, not told the job finished."""
    job_hash = 'a' * 32
    server, _ = _authed_server_with_job(job_hash, 'owner')
    _register_job(server, job_hash, username='owner')

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash, 'job_id': '1',
                                                'username': 'stranger', 'key': 'pass'})

    response = await server.handle_check_progress(mock_request)

    assert response.status == 403
    assert json.loads(response.body) == {'message': 'Error: job belongs to another user.',
                                         'status': JobStatus.REJECTED}


_NO_RECORD = object()

# Every route that names a job. remote_run writes the owner record rather than
# checking it, and check_server names no job, so these four are the whole set.
_JOB_HANDLERS = ["handle_get_results", "handle_check_progress",
                 "handle_cancel_job", "handle_delete_job"]

# name, auth enabled, recorded owner, who is asking, is it refused
_OWNERSHIP_CASES = [
    ("owner may act on their own job", True, "owner", "owner", False),
    ("a stranger may not", True, "owner", "stranger", True),
    ("an unowned job is open to an authenticated stranger", True, None, "stranger", False),
    ("an unowned job is open with no authentication", False, None, None, False),
    ("a job predating the owner record is open", False, _NO_RECORD, None, False),
]


def _server_holding_job(job_hash, owner, auth, node='step0'):
    """A server with one job set up so that every handler has something to act on."""
    server = _make_server(auth=auth)
    if auth:
        server.user_keys = {'owner': {'password': 'pass'},
                            'stranger': {'password': 'pass'}}

    job_dir = os.path.join(server.nfs_mount, job_hash)
    os.makedirs(job_dir, exist_ok=True)
    if owner is not _NO_RECORD:
        with open(os.path.join(job_dir, '.owner'), 'w') as f:
            json.dump({'username': owner}, f)

    # results for get_results to serve
    with tarfile.open(os.path.join(job_dir, f'{job_hash}_{node}.tar.gz'), 'w:gz') as tar:
        info = tarfile.TarInfo(name='test.txt')
        info.size = 0
        tar.addfile(info)

    # a running job for cancel and check_progress to find
    _register_job(server, job_hash,
                  username=None if owner in (None, _NO_RECORD) else owner)
    return server


def _job_request(handler, job_hash, username, node='step0'):
    """Builds the request a given handler expects, carrying credentials when named."""
    params = {'job_hash': job_hash}
    if handler == "handle_check_progress":
        params['job_id'] = '1'
    if username:
        params['username'] = username
        params['key'] = 'pass'

    request = Mock()
    if handler == "handle_get_results":
        # this one takes the hash from the URL rather than the body
        del params['job_hash']
        params['node'] = node
        request.match_info = {'job_hash': job_hash}
    request.json = AsyncMock(return_value=params)
    return request


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", _JOB_HANDLERS)
@pytest.mark.parametrize("case,auth,owner,caller,refused", _OWNERSHIP_CASES,
                         ids=[c[0] for c in _OWNERSHIP_CASES])
async def test_job_ownership(handler, case, auth, owner, caller, refused):
    """Every handler that names a job agrees on who may act on it.

    The unowned rows matter as much as the refused one: a job submitted without
    authentication has no owner, and anybody holding its hash may act on it. That is
    this server's intended behaviour, so it is asserted rather than left to be
    tightened by accident.
    """
    job_hash = 'a' * 32
    server = _server_holding_job(job_hash, owner, auth)

    response = await getattr(server, handler)(_job_request(handler, job_hash, caller))

    if refused:
        assert response.status == 403, case
        assert json.loads(response.body)['message'] == \
            'Error: job belongs to another user.'
    else:
        # what a permitted request answers is each handler's own business; that it
        # was not refused is this test's
        assert response.status != 403, case


###########################
# handle_cancel_job
###########################

@pytest.mark.asyncio
async def test_handle_cancel_job_not_running():
    '''A job the server is not tracking cannot be canceled'''
    server = _make_server()

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': '0' * 32})

    response = await server.handle_cancel_job(mock_request)

    assert response.status == 404
    body = json.loads(response.body)
    assert body['success'] is False
    assert server.sc_canceled_jobs == set()


@pytest.mark.asyncio
async def test_handle_cancel_job_local():
    '''Canceling a locally-running job marks it, and says what that means'''
    server = _make_server(cluster='local')
    job_hash = 'a' * 32
    job_name = _register_job(server, job_hash)

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash})

    with patch('siliconcompiler.remote.server.SlurmSchedulerNode.cancel_nodes') as mock_cancel:
        response = await server.handle_cancel_job(mock_request)

    assert response.status == 200
    body = json.loads(response.body)
    assert body['success'] is True
    assert 'finish on their own' in body['message']
    assert server.sc_canceled_jobs == {job_name}
    assert not mock_cancel.called


@pytest.mark.asyncio
async def test_handle_cancel_job_authenticated():
    '''The job is looked up under its authenticated name'''
    server = _make_server(auth=True)
    server.user_keys = {'testuser': {'password': 'pass', 'compute_time': 0, 'bandwidth': 0}}

    job_hash = 'b' * 32
    job_name = _register_job(server, job_hash, username='testuser')
    assert job_name == f'testuser_{job_hash}'

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash,
                                                'username': 'testuser',
                                                'key': 'pass'})

    response = await server.handle_cancel_job(mock_request)

    assert response.status == 200
    assert server.sc_canceled_jobs == {job_name}


@pytest.mark.asyncio
async def test_handle_cancel_job_auth_error():
    '''A bad key cannot cancel someone else's job'''
    server = _make_server(auth=True)
    server.user_keys = {'testuser': {'password': 'pass', 'compute_time': 0, 'bandwidth': 0}}

    job_hash = 'c' * 32
    _register_job(server, job_hash, username='testuser')

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash,
                                                'username': 'testuser',
                                                'key': 'wrong'})

    response = await server.handle_cancel_job(mock_request)

    assert response.status == 403
    assert server.sc_canceled_jobs == set()


@pytest.mark.asyncio
@pytest.mark.parametrize('params', [{}, {'job_hash': 'not-a-hash'}, {'job_hash': '../etc'}])
async def test_handle_cancel_job_invalid_params(params):
    '''cancel_job takes a job hash, and only a job hash'''
    server = _make_server()

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value=params)

    response = await server.handle_cancel_job(mock_request)

    assert response.status == 400


@pytest.mark.asyncio
async def test_handle_cancel_job_slurm():
    '''Slurm nodes are handed to scancel by name; finished ones are left alone'''
    server = _make_server(cluster='slurm')
    job_hash = 'd' * 32
    _register_job(server, job_hash, nodes={
        'stepone0': {'status': NodeStatus.SUCCESS, 'step': 'stepone', 'index': '0'},
        'steptwo0': {'status': NodeStatus.RUNNING, 'step': 'steptwo', 'index': '0'},
        'stepthree0': {'status': NodeStatus.PENDING, 'step': 'stepthree', 'index': '0'},
    })

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash})

    with patch('siliconcompiler.remote.server.SlurmSchedulerNode.cancel_nodes') as mock_cancel:
        response = await server.handle_cancel_job(mock_request)

    assert response.status == 200
    assert json.loads(response.body)['message'] == f'Canceling job: {job_hash}.'

    # Finished nodes have nothing left to cancel, so they are not sent on.
    mock_cancel.assert_called_once_with(job_hash, [('steptwo', '0'), ('stepthree', '0')])


@pytest.mark.asyncio
async def test_handle_cancel_job_no_scancel(caplog):
    '''A host that cannot cancel slurm nodes says so, and still marks the job'''
    server = _make_server(cluster='slurm')
    job_hash = 'e' * 32
    _register_job(server, job_hash)

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash})

    with patch('siliconcompiler.remote.server.SlurmSchedulerNode.cancel_nodes',
               return_value=[]):
        response = await server.handle_cancel_job(mock_request)

    assert response.status == 200
    assert server.sc_canceled_jobs == {server.job_name(None, job_hash)}
    assert f'Unable to cancel nodes for job: {job_hash}' in caplog.text


@pytest.mark.asyncio
async def test_handle_cancel_job_then_check_progress():
    '''check_progress reports a canceled job as canceled, which ends the
       client's wait loop'''
    server = _make_server()
    job_hash = 'f' * 32
    _register_job(server, job_hash)

    progress_request = Mock()
    progress_request.json = AsyncMock(return_value={'job_hash': job_hash, 'job_id': '0'})

    response = await server.handle_check_progress(progress_request)
    assert json.loads(response.body)['status'] == JobStatus.RUNNING

    cancel_request = Mock()
    cancel_request.json = AsyncMock(return_value={'job_hash': job_hash})
    assert (await server.handle_cancel_job(cancel_request)).status == 200

    progress_request.json = AsyncMock(return_value={'job_hash': job_hash, 'job_id': '0'})
    response = await server.handle_check_progress(progress_request)
    assert json.loads(response.body)['status'] == JobStatus.CANCELED


###########################
# check_progress per-node reporting
###########################

@pytest.mark.asyncio
async def test_handle_check_progress_elapsed_time():
    '''Running nodes report how long they have been going, finished ones how
       long they took'''
    server = _make_server()
    job_hash = '1' * 32
    now = time.time()
    _register_job(server, job_hash, nodes={
        'stepone0': {'status': NodeStatus.SUCCESS, 'step': 'stepone', 'index': '0',
                     'starttime': now - 3725, 'endtime': now - 3600},
        'steptwo0': {'status': NodeStatus.RUNNING, 'step': 'steptwo', 'index': '0',
                     'starttime': now - 65},
        'stepthree0': {'status': NodeStatus.PENDING, 'step': 'stepthree', 'index': '0'},
    })

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash, 'job_id': '0'})

    response = await server.handle_check_progress(mock_request)
    message = json.loads(response.body)['message']

    assert message['stepone0']['elapsed_time'] == '0:02:05'
    assert message['steptwo0']['elapsed_time'] == '0:01:05'
    # A node that has not started has no elapsed time to report.
    assert 'elapsed_time' not in message['stepthree0']


@pytest.mark.asyncio
async def test_handle_check_progress_hides_bookkeeping():
    '''The timestamps and the node address are the server's own, and are not
       part of the reported payload'''
    server = _make_server()
    job_hash = '2' * 32
    _register_job(server, job_hash, nodes={
        'stepone0': {'status': NodeStatus.RUNNING, 'step': 'stepone', 'index': '0',
                     'starttime': time.time()},
    })

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash, 'job_id': '0'})

    response = await server.handle_check_progress(mock_request)
    message = json.loads(response.body)['message']

    assert set(message['stepone0']) == {'status', 'elapsed_time'}


@pytest.mark.asyncio
async def test_handle_check_progress_claimed_job():
    '''A job claimed by handle_remote_run but not yet set up by remote_sc is
       still running, not completed'''
    server = _make_server()
    job_hash = '3' * 32
    server.sc_jobs[job_hash] = {}

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash, 'job_id': '0'})

    response = await server.handle_check_progress(mock_request)
    body = json.loads(response.body)

    assert body['status'] == JobStatus.RUNNING
    assert body['message'] == {}


###########################
# Routing
###########################

def test_server_routes():
    '''Every documented endpoint is routed, and results are not served
       statically'''
    from aiohttp.web_urldispatcher import StaticResource

    server = _make_server()

    with patch("aiohttp.web.run_app"):
        server.run()

    routed = set()
    for route in server.app.router.routes():
        assert not isinstance(route.resource, StaticResource), \
            'nfs_mount must not be served as a static route'
        routed.add((route.method, route.resource.canonical))

    assert routed == {
        ('POST', '/remote_run/'),
        ('POST', '/check_progress/'),
        ('POST', '/check_server/'),
        ('POST', '/cancel_job/'),
        ('POST', '/delete_job/'),
        ('POST', '/get_results/{job_hash}.tar.gz'),
    }


def test_server_run_creates_staging():
    '''run() prepares the upload staging directory'''
    server = _make_server()

    with patch("aiohttp.web.run_app"):
        server.run()

    assert os.path.isdir(server.staging_mount)
    assert os.path.dirname(server.staging_mount) == server.nfs_mount


###########################
# Upload staging
###########################

class _MockPart:
    def __init__(self, name, data=None, chunks=None):
        self.name = name
        self._data = data
        self._chunks = list(chunks or [])

    async def json(self):
        return self._data

    async def read_chunk(self):
        if self._chunks:
            return self._chunks.pop(0)
        return None


def _upload_request(cfg, archive=None):
    '''A mock multipart 'remote_run' request carrying a manifest and an
       optional uploaded archive.'''
    parts = []
    if archive is not None:
        parts.append(_MockPart('import', chunks=[archive]))
    parts.append(_MockPart('params', data={'cfg': cfg, 'params': {}}))

    class MockReader:
        async def next(self):
            if parts:
                return parts.pop(0)
            return None

    request = Mock()

    async def get_multipart():
        return MockReader()
    request.multipart = get_multipart
    return request


@pytest.mark.asyncio
async def test_handle_remote_run_stages_upload(gcd_nop_project):
    '''The uploaded archive is staged outside nfs_mount and removed once
       extracted'''
    server = _make_server()

    tar_path = os.path.join(tempfile.mkdtemp(), 'upload.tar.gz')
    with tarfile.open(tar_path, 'w:gz') as tar:
        info = tarfile.TarInfo(name='test.txt')
        info.size = 0
        tar.addfile(info)
    with open(tar_path, 'rb') as f:
        archive = f.read()

    request = _upload_request(gcd_nop_project.getdict(), archive=archive)

    with patch.object(Server, 'remote_sc', autospec=True) as mock_run:
        response = await server.handle_remote_run(request)
        job_hash = json.loads(response.body)['job_hash']

        assert response.status == 200
        # The job is claimed before the thread that runs it gets going.
        assert job_hash in server.sc_jobs
        assert server.sc_job_threads[job_hash]['jobhash'] == job_hash
        server.sc_job_threads[job_hash]['thread'].join(timeout=10)
        assert mock_run.called

    assert os.listdir(server.staging_mount) == []
    # The extracted job directory is what remains under the mount.
    assert sorted(os.listdir(server.nfs_mount)) == ['.staging', job_hash]


@pytest.mark.asyncio
async def test_handle_remote_run_removes_failed_upload(gcd_nop_project):
    '''A staged upload that cannot be extracted is still cleaned up'''
    server = _make_server()

    request = _upload_request(gcd_nop_project.getdict(), archive=b'not a tarball')

    with patch.object(Server, 'remote_sc', autospec=True) as mock_run:
        with pytest.raises(tarfile.ReadError):
            await server.handle_remote_run(request)

    assert not mock_run.called
    assert os.listdir(server.staging_mount) == []


###########################
# Job bookkeeping
###########################

def test_remote_sc_tracks_and_clears_nodes(gcd_nop_project, monkeypatch):
    '''remote_sc publishes the node list while the job runs, and takes it back
       down afterwards'''
    server = _make_server()
    job_hash = '4' * 32
    gcd_nop_project.set('record', 'remoteid', job_hash)

    tracked = {}

    def fake_run():
        tracked.update(server.sc_jobs[job_hash])
        return True
    monkeypatch.setattr(gcd_nop_project, 'run', fake_run)

    server.remote_sc(gcd_nop_project, None)

    assert set(tracked) == {None, 'stepone0', 'steptwo0'}
    # The node's address is recorded, because 'stepone0' cannot be split back
    # into a step and an index.
    assert (tracked['stepone0']['step'], tracked['stepone0']['index']) == ('stepone', '0')

    assert server.sc_jobs == {}
    assert server.sc_project_lookup == {}


def test_remote_sc_clears_tracking_on_failure(gcd_nop_project, monkeypatch):
    '''A job whose run raises is over, and must not be reported as running'''
    server = _make_server()
    job_hash = '5' * 32
    gcd_nop_project.set('record', 'remoteid', job_hash)

    def boom():
        raise RuntimeError('run failed')
    monkeypatch.setattr(gcd_nop_project, 'run', boom)

    server.sc_job_threads[job_hash] = {'thread': Mock(), 'jobhash': job_hash}

    with pytest.raises(RuntimeError):
        server.remote_sc(gcd_nop_project, None)

    assert server.sc_jobs == {}
    assert server.sc_job_threads == {}
    assert server.sc_project_lookup == {}


@pytest.mark.asyncio
async def test_shutdown_cancels_running_jobs():
    '''Shutting down with a job in flight cancels it rather than abandoning
       whatever it submitted'''
    server = _make_server(cluster='slurm')
    job_hash = '6' * 32
    job_name = _register_job(server, job_hash)

    thread = Mock()
    thread.is_alive.return_value = False
    server.sc_job_threads[job_name] = {'thread': thread, 'jobhash': job_hash}

    with patch("aiohttp.web.run_app"):
        server.run()

    server.app.freeze()
    with patch('siliconcompiler.remote.server.SlurmSchedulerNode.cancel_nodes') as mock_cancel, \
            patch('siliconcompiler.remote.server.TaskScheduler.halt_all') as mock_halt:
        await server.app.cleanup()

    assert job_name in server.sc_canceled_jobs
    mock_cancel.assert_called_once_with(job_hash, [('stepone', '0')])
    # Node processes are not the scheduler's to leave behind either: they are
    # joined at interpreter exit, so shutting down has to end them.
    mock_halt.assert_called_once()
    thread.join.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_with_no_jobs():
    '''Shutdown is a no-op when nothing is running'''
    server = _make_server()

    with patch("aiohttp.web.run_app"):
        server.run()

    server.app.freeze()
    with patch('siliconcompiler.remote.server.SlurmSchedulerNode.cancel_nodes') as mock_cancel, \
            patch('siliconcompiler.remote.server.TaskScheduler.halt_all') as mock_halt:
        await server.app.cleanup()

    assert not mock_cancel.called
    assert not mock_halt.called


###########################
# Live server
###########################

@pytest.mark.timeout(60)
def test_server_does_not_serve_mount(scserver, scserver_nfs_path):
    '''A GET cannot walk out of the results endpoint into the mount'''
    port = scserver()

    # run() writes this file, so it is certainly there to be served.
    assert os.path.isfile(os.path.join(scserver_nfs_path, '.gitignore'))

    resp = requests.get(f'http://localhost:{port}/get_results/.gitignore', timeout=10)
    assert resp.status_code == 404

    # The results path itself exists, but only as a POST.
    resp = requests.get(f'http://localhost:{port}/get_results/{"0" * 32}.tar.gz',
                        timeout=10)
    assert resp.status_code == 405


@pytest.mark.timeout(60)
def test_server_cancel_job_endpoint(scserver):
    '''cancel_job is routed on a running server, not just implemented'''
    port = scserver()

    resp = requests.post(f'http://localhost:{port}/cancel_job/',
                         data=json.dumps({'job_hash': '0' * 32}),
                         timeout=10)

    # An unrouted path would answer with aiohttp's own plain-text 404 instead.
    assert resp.status_code == 404
    assert resp.json() == {'message': 'Job is not running.', 'success': False}


@pytest.mark.asyncio
async def test_handle_delete_job_archive_only():
    '''A job whose directory is already gone still has its archive deleted'''
    server = _make_server()

    job_hash = '7' * 32
    tar_file = os.path.join(server.nfs_mount, f'{job_hash}.tar.gz')
    with tarfile.open(tar_file, 'w:gz') as tar:
        info = tarfile.TarInfo(name='test.txt')
        info.size = 0
        tar.addfile(info)

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={'job_hash': job_hash})

    response = await server.handle_delete_job(mock_request)

    assert response.status == 200
    assert not os.path.exists(tar_file)


###########################
# Upload size
###########################

def test_max_upload_size_default():
    '''A job is as big as it is: the server does not cap it unless told to'''
    server = Server()

    assert server.get('option', 'maxuploadsize') == 0
    # Not 0: aiohttp's multipart reader treats 0 as "reject everything".
    assert server.max_upload_size == sys.maxsize


def test_max_upload_size_in_bytes():
    '''The option is in MB, aiohttp wants bytes'''
    server = Server()
    server.set('option', 'maxuploadsize', 512)

    assert server.max_upload_size == 512 * 1024 * 1024


def test_server_app_gets_upload_limit():
    '''The limit reaches the application, not just the schema'''
    server = _make_server()
    server.set('option', 'maxuploadsize', 5)

    with patch("aiohttp.web.Application") as mock_app, patch("aiohttp.web.run_app"):
        server.run()

    mock_app.assert_called_once_with(client_max_size=5 * 1024 * 1024)


def _oversized_upload():
    '''A remote_run body too big for aiohttp's 1MB default.

    The bulk is in the 'params' part, which is where a real submission carries
    its weight: the manifest is sent as JSON there, runs to several MB for an
    ordinary design, and is read whole rather than streamed.
    '''
    return {
        'params': json.dumps({'params': {}, 'filler': 'x' * (2 * 1024 * 1024)}),
        'import': ('job.tar.gz', b'0' * (2 * 1024 * 1024))
    }


@pytest.mark.timeout(60)
def test_server_accepts_large_upload(scserver):
    '''An upload past aiohttp's 1MB default body limit is accepted'''
    port = scserver()

    resp = requests.post(f'http://localhost:{port}/remote_run/',
                         files=_oversized_upload(), timeout=30)

    # The body was read and parsed: this is the handler's own answer to a
    # request that carried no manifest, not a rejection of its size.
    assert resp.status_code == 400
    assert 'Manifest not provided' in resp.json()['message']


@pytest.mark.timeout(60)
def test_server_enforces_upload_limit(scserver):
    '''A configured limit is enforced'''
    port = scserver(extra_args=['-maxuploadsize', '1'])

    resp = requests.post(f'http://localhost:{port}/remote_run/',
                         files=_oversized_upload(), timeout=30)

    assert resp.status_code == 413


###########################
# Progress callbacks
###########################

def _callback_project(server, job_hash):
    '''A project set up the way remote_sc() leaves one for the callbacks:
       build directory under the job's own root on the mount.'''
    from siliconcompiler import Project, Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask
    from siliconcompiler.utils.paths import jobdir

    project = Project('cbdesign')
    flow = Flowgraph("cbflow")
    flow.node("stepone", NOPTask())
    project.set_flow(flow)
    project.set('record', 'remoteid', job_hash)

    job_root = os.path.join(server.nfs_mount, job_hash)
    project.set('option', 'builddir', job_root)
    os.makedirs(jobdir(project), exist_ok=True)
    project.write_manifest(os.path.join(jobdir(project), f'{project.name}.pkg.json'))

    server.sc_project_lookup[project] = {"name": job_hash, "jobhash": job_hash}
    server.sc_jobs[job_hash] = {
        None: {'status': RemoteNodeStatus.PENDING},
        'stepone0': {'status': RemoteNodeStatus.PENDING, 'step': 'stepone', 'index': '0'}
    }

    return project, job_root


def test_run_start_publishes_node_statuses():
    '''The pre_run callback archives the starting manifest and publishes the
       statuses the job starts from'''
    server = _make_server()
    job_hash = 'a' * 32
    project, job_root = _callback_project(server, job_hash)

    project.set('record', 'status', NodeStatus.SUCCESS, step='stepone', index='0')

    server._Server__run_start(project)

    assert os.path.isfile(os.path.join(job_root, f'{job_hash}_None.tar.gz'))
    assert server.sc_jobs[job_hash][None]['status'] == NodeStatus.SUCCESS
    assert server.sc_jobs[job_hash]['stepone0']['status'] == NodeStatus.SUCCESS


def test_run_start_ignores_untracked_nodes():
    '''A node the job is not reporting on is skipped rather than invented'''
    server = _make_server()
    job_hash = 'b' * 32
    project, _ = _callback_project(server, job_hash)

    del server.sc_jobs[job_hash]['stepone0']

    server._Server__run_start(project)

    assert set(server.sc_jobs[job_hash]) == {None}


def test_node_start_stamps_start_time():
    '''The pre_node callback marks the node running and starts its clock'''
    server = _make_server()
    job_hash = 'c' * 32
    project, _ = _callback_project(server, job_hash)

    before = time.time()
    server._Server__node_start(project, 'stepone', '0')

    node = server.sc_jobs[job_hash]['stepone0']
    assert node['status'] == NodeStatus.RUNNING
    assert before <= node['starttime'] <= time.time()


def test_node_end_archives_and_stops_the_clock():
    '''The post_node callback archives the node and freezes its elapsed time'''
    server = _make_server()
    job_hash = 'd' * 32
    project, job_root = _callback_project(server, job_hash)

    server._Server__node_start(project, 'stepone', '0')
    project.set('record', 'status', NodeStatus.SUCCESS, step='stepone', index='0')

    server._Server__node_end(project, 'stepone', '0')

    assert os.path.isfile(os.path.join(job_root, f'{job_hash}_stepone0.tar.gz'))
    node = server.sc_jobs[job_hash]['stepone0']
    assert node['status'] == NodeStatus.SUCCESS
    assert node['endtime'] >= node['starttime']


###########################
# Remaining server paths
###########################

def test_run_loads_users_json():
    '''run() imports the user table when authentication is on'''
    server = _make_server(auth=True)

    users = {'users': [
        {'username': 'user1', 'password': 'pass1', 'compute_time': 100, 'bandwidth': 50},
        {'username': 'user2', 'password': 'pass2'}
    ]}
    with open(os.path.join(server.nfs_mount, 'users.json'), 'w') as f:
        json.dump(users, f)

    with patch("aiohttp.web.run_app"):
        server.run()

    assert server.user_keys == {
        'user1': {'password': 'pass1', 'compute_time': 100, 'bandwidth': 50},
        'user2': {'password': 'pass2', 'compute_time': 0, 'bandwidth': 0}
    }


def test_run_warns_on_unusable_users_json(caplog):
    '''A user table that cannot be read leaves the server with no users'''
    server = _make_server(auth=True)

    with open(os.path.join(server.nfs_mount, 'users.json'), 'w') as f:
        f.write('not json')

    with patch("aiohttp.web.run_app"):
        server.run()

    assert server.user_keys == {}
    assert "Could not find well-formatted 'users.json'" in caplog.text


@pytest.mark.asyncio
async def test_handle_remote_run_invalid_params(gcd_nop_project):
    '''remote_run validates its parameters like every other endpoint'''
    server = _make_server()

    request = Mock()

    async def get_multipart():
        parts = [_MockPart('params', data={'cfg': gcd_nop_project.getdict(),
                                           'params': {'bogus': 'value'}})]

        class MockReader:
            async def next(self):
                if parts:
                    return parts.pop(0)
                return None
        return MockReader()
    request.multipart = get_multipart

    response = await server.handle_remote_run(request)

    assert response.status == 400


def test_run_job_marks_finished_nodes_uploaded(gcd_nop_project, monkeypatch):
    '''A node the client already ran is reported as uploaded, not pending'''
    server = _make_server()
    job_hash = 'e' * 32
    gcd_nop_project.set('record', 'remoteid', job_hash)
    gcd_nop_project.set('record', 'status', NodeStatus.SUCCESS, step='stepone', index='0')

    tracked = {}
    monkeypatch.setattr(gcd_nop_project, 'run',
                        lambda: tracked.update(server.sc_jobs[job_hash]) or True)

    server.remote_sc(gcd_nop_project, None)

    assert tracked['stepone0']['status'] == RemoteNodeStatus.UPLOADED
    assert tracked['steptwo0']['status'] == NodeStatus.PENDING


@pytest.mark.parametrize('cluster', ('slurm', 'docker'))
def test_run_job_uses_cluster_scheduler(gcd_nop_project, monkeypatch, cluster):
    '''A clustered server hands its nodes to that cluster's scheduler'''
    server = _make_server(cluster=cluster)
    gcd_nop_project.set('record', 'remoteid', 'f' * 32)

    monkeypatch.setattr(gcd_nop_project, 'run', lambda: True)

    server.remote_sc(gcd_nop_project, None)

    assert gcd_nop_project.option.scheduler.get_name() == cluster


def test_run_job_leaves_scheduler_unset_when_local(gcd_nop_project, monkeypatch):
    '''A local server does not name a per-node scheduler'''
    server = _make_server(cluster='local')
    gcd_nop_project.set('record', 'remoteid', 'f' * 32)

    monkeypatch.setattr(gcd_nop_project, 'run', lambda: True)

    server.remote_sc(gcd_nop_project, None)

    assert gcd_nop_project.option.scheduler.get_name() is None


@pytest.mark.asyncio
async def test_shutdown_warns_when_job_will_not_stop(caplog):
    '''A job that outlives the shutdown timeout is reported, not waited on'''
    server = _make_server()
    job_hash = '8' * 32
    job_name = _register_job(server, job_hash)

    thread = Mock()
    thread.is_alive.return_value = True
    server.sc_job_threads[job_name] = {'thread': thread, 'jobhash': job_hash}

    with patch("aiohttp.web.run_app"):
        server.run()

    server.app.freeze()
    with patch('siliconcompiler.remote.server.TaskScheduler.halt_all'):
        await server.app.cleanup()

    assert f'Job did not stop in time: {job_hash}' in caplog.text


@pytest.mark.asyncio
async def test_shutdown_tolerates_job_finishing_first():
    '''A job that ends between being listed and being canceled is left alone'''
    server = _make_server(cluster='slurm')
    job_hash = '9' * 32
    job_name = server.job_name(None, job_hash)

    thread = Mock()
    thread.is_alive.return_value = False
    # Registered as running, but already gone from sc_jobs.
    server.sc_job_threads[job_name] = {'thread': thread, 'jobhash': job_hash}

    with patch("aiohttp.web.run_app"):
        server.run()

    server.app.freeze()
    with patch('siliconcompiler.remote.server.SlurmSchedulerNode.cancel_nodes') as mock_cancel, \
            patch('siliconcompiler.remote.server.TaskScheduler.halt_all'):
        await server.app.cleanup()

    assert not mock_cancel.called
    assert server.sc_canceled_jobs == set()


@pytest.mark.timeout(60)
@pytest.mark.parametrize('job_hash', [
    '%2e%2e%2f%2e%2e%2fetc%2fpasswd',
    '..%2f..%2fsecret',
    '%2E%2E%2Fsecret',
    'notahash',
    'A' * 32,
])
def test_server_get_results_rejects_bad_job_hash(scserver, scserver_nfs_path, job_hash):
    '''A job hash from the URL cannot walk out of the mount.

    aiohttp percent-decodes a path segment into match_info, so '%2e%2e%2f'
    reaches the handler as '../' -- the hash has to be validated before it is
    joined onto a path, not merely matched by the route.
    '''
    port = scserver()

    resp = requests.post(f'http://localhost:{port}/get_results/{job_hash}.tar.gz',
                         data=json.dumps({}), timeout=10)

    assert resp.status_code == 400
    assert 'Invalid parameters' in resp.json()['message']


@pytest.mark.timeout(60)
def test_server_get_results_cannot_escape_mount(scserver, scserver_nfs_path):
    '''The traversal that reaches a real file outside the mount is refused.

    Escaping needs the path to stay resolvable, so this lays out what an
    unchecked hash of '../x' resolves to: a sibling directory of the mount, and
    the archive name the handler builds, one level above it.
    '''
    outside = os.path.dirname(scserver_nfs_path)
    os.makedirs(os.path.join(outside, 'x'), exist_ok=True)
    with open(os.path.join(outside, 'x_None.tar.gz'), 'w') as f:
        f.write('not yours')

    port = scserver()

    resp = requests.post(f'http://localhost:{port}/get_results/..%2fx.tar.gz',
                         data=json.dumps({}), timeout=10)

    assert resp.status_code == 400
    assert 'not yours' not in resp.text


@pytest.mark.asyncio
async def test_handle_get_results_non_object_body():
    '''A body that is not an object is rejected, not indexed into'''
    server = _make_server()

    mock_request = Mock()
    mock_request.json = AsyncMock(return_value=['not', 'an', 'object'])
    mock_request.match_info = {'job_hash': '0' * 32}

    response = await server.handle_get_results(mock_request)

    assert response.status == 400
