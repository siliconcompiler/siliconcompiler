import os
import subprocess
from ..fixtures import test_wrapper

##################################
def test_gcd_floorplan():
    '''Floorplan API test: build the GCD example using a Python-based floorplan
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/asic')] + '/examples/gcd/'

    # Run the build command.
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-target', 'freepdk45',
                    '-asic_floorplan', gcd_ex_dir + '/floorplan.py',
                    '-constraint', gcd_ex_dir + '/gcd.sdc',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.svg')
