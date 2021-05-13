import os
import subprocess
# fixture automatically used when imported to create clean build dir
from ..fixtures import test_wrapper

##################################
def test_nextpnr():
    '''Basic FPGA test: build the Blinky example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    blinky_ex_dir = os.path.abspath(__file__)
    blinky_ex_dir = blinky_ex_dir[:blinky_ex_dir.rfind('/tests/fpga')] + '/examples/blinky/'

    # Run the build command.
    subprocess.run(['sc',
                    blinky_ex_dir + '/blinky.v',
                    '-design', 'blinky',
                    '-target', 'ice40_nextpnr',
                    '-constraint', blinky_ex_dir + '/icebreaker.pcf'],
                   stdout = subprocess.DEVNULL)

    # Verify that a bitstream was generated
    assert os.path.isfile('build/blinky/job1/export/outputs/blinky.bit')
