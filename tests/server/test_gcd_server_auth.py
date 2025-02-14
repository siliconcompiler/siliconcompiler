import os
import pytest
import siliconcompiler


###########################
@pytest.mark.eda
@pytest.mark.timeout(600)
def test_gcd_server_authenticated(gcd_chip, scserver, scserver_users, scserver_credential):
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
    scserver_credential(port, user, user_pwd, chip=gcd_chip)

    gcd_chip.set('option', 'nodisplay', True)

    # Run remote build.
    assert gcd_chip.run()

    # Verify that GDS file was generated and returned.
    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')


###########################
@pytest.mark.eda
@pytest.mark.timeout(600)
def test_gcd_server_not_authenticated(gcd_chip, scserver, scserver_users, scserver_credential):
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
    gcd_chip.set('option', 'nodisplay', True)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = scserver_credential(port, user, user_pwd + '1')

    # Add remote parameters.
    gcd_chip.set('option', 'remote', True)
    gcd_chip.set('option', 'credentials', tmp_creds)

    # Run remote build. It should fail, so catch the expected exception.
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run(raise_exception=True)

    # Verify that GDS was not generated.
    assert not os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')
