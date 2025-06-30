import pytest

import os.path

from siliconcompiler import NodeStatus


###########################
def test_server_authenticated(gcd_nop_project, scserver, scserver_users, scserver_credential):
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

    # Create the temporary credentials file, and set the Chip to use it.
    scserver_credential(port, user, user_pwd, chip=gcd_nop_project)

    gcd_nop_project.set('option', 'nodisplay', True)

    # Run remote build.
    assert gcd_nop_project.run()

    # Verify that GDS file was generated and returned.
    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')

    assert gcd_nop_project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS
    assert gcd_nop_project.get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS


###########################
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

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = scserver_credential(port, user, user_pwd + '1')

    # Add remote parameters.
    gcd_nop_project.set('option', 'remote', True)
    gcd_nop_project.set('option', 'credentials', tmp_creds)

    # Run remote build. It should fail, so catch the expected exception.
    with pytest.raises(RuntimeError, match="Server responded with 403: Authentication error."):
        gcd_nop_project.run(raise_exception=True)


def test_server(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_project = gcd_remote_test()

    # Run the remote job.
    assert gcd_project.run()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')

    assert gcd_project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS
    assert gcd_project.get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS


###########################
def test_server_partial(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test runs a partial flowgraph on the remote server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_project = gcd_remote_test()

    # Set from/to to limit how many steps are run on the remote host.
    gcd_project.set('option', 'to', ['stepone'])

    # Run the remote job.
    assert gcd_project.run()

    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert not os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')

    assert gcd_project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS
    assert gcd_project.get("record", "status", step="steptwo", index="0") == NodeStatus.PENDING


@pytest.mark.eda
@pytest.mark.quick
def test_server_slurm(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_project = gcd_remote_test(use_slurm=True)

    # Run the remote job.
    gcd_project.run(raise_exception=True)

    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')

    assert gcd_project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS
    assert gcd_project.get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS
