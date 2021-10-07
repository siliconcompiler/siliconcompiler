import os
import subprocess

if __name__ != "__main__":
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
                    '-constraint', blinky_ex_dir + '/icebreaker.pcf',
                    '-design', 'blinky',
                    '-target', 'fpgaflow_ice40up5k-sg48'])

    # Verify that a bitstream was generated
    assert os.path.isfile('build/blinky/job0/bitstream/0/outputs/blinky.bit')

if __name__ == "__main__":
    test_icebreaker()
