import os
import re
import siliconcompiler
import subprocess
import traceback

from unittest.mock import Mock

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

###########################
def test_gcd_server():
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'])

    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/quick_tests/asic')] + '/examples/gcd/'

    # Create instance of Chip class
    chip = siliconcompiler.Chip()

    # Mock the _runstep method.
    old__runstep = chip._runstep
    def mocked_runstep(*args, **kwargs):
        if args[0] == 'import':
            old__runstep(*args)
        else:
            chip.logger.error('Non-import step run locally in remote job!')
    chip._runstep = Mock()
    chip._runstep.side_effect = mocked_runstep

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    # Inserting value into configuration
    chip.set('design', 'gcd', clobber=True)
    chip.target("asicflow_freepdk45")
    chip.add('source', gcd_ex_dir + 'gcd.v')
    chip.set('clock', 'clock_name', 'pin', 'clk')
    chip.add('constraint', gcd_ex_dir + 'gcd.sdc')
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.set('remote', 'addr', 'localhost')
    chip.set('remote', 'port', '8080')
    chip.set('quiet', 'true', clobber=True)
    chip.set('relax', 'true', clobber=True)

    # Run the remote job.
    try:
        chip.run()
    except:
        # Failures will be printed, and noted in the following assert.
        traceback.print_exc()

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS and SVG files were generated and returned.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

if __name__ == "__main__":
    test_gcd_server()
