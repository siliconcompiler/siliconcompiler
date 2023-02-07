import json
import os
import siliconcompiler
import subprocess
import traceback
import pytest
import time

from unittest.mock import Mock

@pytest.fixture
def gcd_remote_test(gcd_chip, request):
    # Get the port number; avoid re-use to enable parallel tests.
    if 'port' in request.keywords:
        port = request.keywords["port"]
    else:
        port = '8080'

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-port', port,
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'])
    time.sleep(3)

    # Mock the _runstep method.
    old__runtask = gcd_chip._runtask
    def mocked_runtask(*args, **kwargs):
        if args[0] == 'import':
            old__runtask(*args)
        else:
            gcd_chip.logger.error('Non-import step run locally in remote job!')
    gcd_chip._runtask = Mock()
    gcd_chip._runtask.side_effect = mocked_runtask

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost', 'port': int(port)}))
    gcd_chip.set('option', 'remote', True)
    gcd_chip.set('option', 'credentials', os.path.abspath(tmp_creds))

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    try:
        yield gcd_chip
    except Exception as e:
        # Kill the server process.
        srv_proc.kill()
        # Re-raise the exception.
        raise e

    # Kill the server process.
    srv_proc.kill()


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.remote_test(port='8080')
def test_gcd_server(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test

    # Run the remote job.
    try:
        gcd_chip.run()
    except Exception:
        # Failures will be printed, and noted in the following assert.
        traceback.print_exc()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.remote_test(port='8081')
def test_gcd_server_partial(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test runs a partial flowgraph on the remote server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test

    # Set a steplist to limit how many steps are run on the remote host.
    gcd_chip.set('option', 'steplist', ['import', 'syn', 'floorplan'])

    # Run the remote job.
    try:
        gcd_chip.run()
    except Exception:
        # Failures will be printed, and noted in the following assert.
        traceback.print_exc()

    # Verify that OpenDB file was created for the floorplan task.
    assert os.path.isfile('build/gcd/job0/floorplan/0/outputs/gcd.odb')
    # Verify that the following physyn step was not run.
    assert not os.path.isfile('build/gcd/job0/physyn/0/outputs/gcd.odb')

###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.remote_test(port='8082')
def test_gcd_server_partial_noeda(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test attempts to run a remote job with no EDA tasks, which should produce an error.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test

    # Set the steplist to only run the import task.
    gcd_chip.set('option', 'steplist', ['import'])

    # Run the remote job.
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        gcd_chip.run()

###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.remote_test(port='8083')
def test_gcd_server_partial_noimport(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test attempts to run a remote job with no import tasks, which should produce an error.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test

    # Set the steplist to only run the synthesis task.
    gcd_chip.set('option', 'steplist', ['syn'])

    # Run the remote job.
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        gcd_chip.run()

###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.remote_test(port='8084')
def test_gcd_server_error(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test attempts to run an invalid flow graph, with two 'import' tasks containing an EDA
       task between them. This should fail, because the current remote flow expects 'import' -> 'EDA'.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test

    # Set an extra import step after the export step, to create an invalid flowgraph.
    gcd_chip.node('asicflow', 'importt', 'surelog', 'import', index='0')
    gcd_chip.edge('asicflow', 'export', 'importt', head_index='0')

    # Run the remote job.
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        gcd_chip.run()

###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.remote_test(port='8085')
def test_gcd_server_argstep_noimport(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test attempts to run a remote job with ('arg', 'step') set. Remote jobs need at least
       one import task and one EDA task, so this should fail.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test

    # Set the '-step' option.
    gcd_chip.set('arg', 'step', 'floorplan')

    # Run the remote job.
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        gcd_chip.run()

if __name__ == "__main__":
    from tests.fixtures import gcd_chip
    if os.path.isdir('local_server_work'):
        os.rmdir('local_server_work')
    cur_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))
    pytest.main(['test_server.py'])
    os.chdir(cur_dir)
