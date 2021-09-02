import os
import subprocess
from tests.fixtures import test_wrapper

###########################
def test_gcd_local_permutations():
    '''Basic permutations test: build two versions of the GCD example
       with slightly different configurations.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/daily_tests/asic')] + '/examples/gcd/'
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-constraint', gcd_ex_dir + '/gcd.sdc',
                    '-permutations', gcd_ex_dir + '/2jobs.py',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Verify that all GDS/SVG files were generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/job2/export/outputs/gcd.gds')
