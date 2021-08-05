import os
import subprocess
# fixture automatically used when imported to create clean build dir
from tests.fixtures import test_wrapper

##################################
def test_icebreaker():
    '''Basic FPGA test: build the Blinky example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    blinky_ex_dir = os.path.abspath(__file__)
    blinky_ex_dir = blinky_ex_dir[:blinky_ex_dir.rfind('/tests/quick_tests/fpga')] + '/examples/blinky/'

    # Run the build command for an iCE40 board.
    subprocess.run(['sc',
                    blinky_ex_dir + '/blinky.v',
                    '-mode', 'fpga',
                    '-design', 'blinky',
                    '-target', 'icebreaker_fpga'],
                   stdout = subprocess.DEVNULL)

    # Verify that a bitstream was generated
    assert os.path.isfile('build/blinky/job1/export/outputs/blinky.bit')

##################################
def test_ice40up5k_evn():
    '''Basic FPGA test: build the Blinky example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    blinky_ex_dir = os.path.abspath(__file__)
    blinky_ex_dir = blinky_ex_dir[:blinky_ex_dir.rfind('/tests/quick_tests/fpga')] + '/examples/blinky/'

    # Run the build command for an iCE40 board.
    subprocess.run(['sc',
                    blinky_ex_dir + '/blinky.v',
                    '-mode', 'fpga',
                    '-design', 'blinky',
                    '-target', 'ice40up5k-evn_fpga'],
                   stdout = subprocess.DEVNULL)

    # Verify that a bitstream was generated
    assert os.path.isfile('build/blinky/job1/export/outputs/blinky.bit')

##################################
def test_orangecrab():
    '''Basic FPGA test: build the Blinky example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    blinky_ex_dir = os.path.abspath(__file__)
    blinky_ex_dir = blinky_ex_dir[:blinky_ex_dir.rfind('/tests/quick_tests/fpga')] + '/examples/blinky/'

    # Run the build command for an ECP5 board.
    subprocess.run(['sc',
                    blinky_ex_dir + '/blinky.v',
                    '-mode', 'fpga',
                    '-design', 'blinky',
                    '-target', 'orangecrab_fpga'],
                   stdout = subprocess.DEVNULL)

    # Verify that a bitstream was generated
    assert os.path.isfile('build/blinky/job1/export/outputs/blinky.bit')
