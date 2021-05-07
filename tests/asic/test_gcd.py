import os
import pathlib
import subprocess
from fixtures import test_wrapper

##################################
def test_gcd_local():
    '''Basic CLI test: build the GCD example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath(str(pathlib.Path(__file__).parent.parent.parent)) + '/examples/gcd/'

    # Run the build command.
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-target', 'freepdk45',
                    '-asic_diesize', '0 0 100.13 100.8',
                    '-asic_coresize', '10.07 11.2 90.25 91',
                    '-constraint', gcd_ex_dir + '/constraint.sdc',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Verify that a GDS file was generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
