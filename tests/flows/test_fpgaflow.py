import os
import subprocess
import pytest

##################################
@pytest.mark.eda
@pytest.mark.quick
def test_icebreaker(scroot):
    '''Basic FPGA test: build the Blinky example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    blinky_ex_dir = os.path.join(scroot, 'examples', 'blinky')

    # Run the build command for an iCE40 board.
    subprocess.run(['sc',
                    os.path.join(blinky_ex_dir, 'blinky.v'),
                    '-constraint', os.path.join(blinky_ex_dir, 'icebreaker.pcf'),
                    '-design', 'blinky',
                    '-target', 'fpgaflow_ice40up5k-sg48'])

    # Verify that a bitstream was generated
    assert os.path.isfile('build/blinky/job0/bitstream/0/outputs/blinky.bit')

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_icebreaker(scroot())
