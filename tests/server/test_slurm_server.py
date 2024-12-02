import os
import traceback
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_gcd_server(gcd_remote_test):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Get the partially-configured GCD Chip object from the fixture.
    gcd_chip = gcd_remote_test(use_slurm=True)

    # Run the remote job.
    try:
        gcd_chip.run()
    except Exception:
        # Failures will be printed, and noted in the following assert.
        traceback.print_exc()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')
