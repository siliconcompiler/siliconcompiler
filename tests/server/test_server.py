import os
import siliconcompiler
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_gcd_server(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test()

    # Run the remote job.
    gcd_chip.run()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_gcd_server_partial(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test runs a partial flowgraph on the remote server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test()

    # Set from/to to limit how many steps are run on the remote host.
    gcd_chip.set('option', 'to', ['floorplan'])

    # Run the remote job.
    gcd_chip.run()

    # Verify that OpenDB file was created for the floorplan task.
    assert os.path.isfile('build/gcd/job0/floorplan/0/outputs/gcd.odb')
    # Verify that the following physyn step was not run.
    assert not os.path.isfile('build/gcd/job0/physyn/0/outputs/gcd.odb')


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_gcd_server_partial_noeda(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test attempts to run a remote job with no EDA tasks, which should produce an error.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test()

    # Set from/to to only run the import task.
    gcd_chip.set('option', 'to', ['import'])

    # Run the remote job.
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_gcd_server_partial_noimport(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test attempts to run a remote job with no import tasks, which should produce an error.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test()

    # Set from/to to only run the synthesis task.
    gcd_chip.set('option', 'from', ['syn'])
    gcd_chip.set('option', 'to', ['syn'])

    # Run the remote job.
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_gcd_server_argstep_noimport(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.

       This test attempts to run a remote job with ('arg', 'step') set. Remote jobs need at least
       one import task and one EDA task, so this should fail.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test()

    # Set the '-step' option.
    gcd_chip.set('arg', 'step', 'floorplan')

    # Run the remote job.
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()
