import os
import subprocess
from tests.fixtures import test_wrapper

##################################
def test_gcd_cli():
    '''Basic CLI test: build the GCD example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/daily_tests/asic')] + '/examples/gcd/'

    # Run the build command.
    subprocess.run([f'{gcd_ex_dir}/run.sh'], stdout = subprocess.DEVNULL)

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job0/export0/outputs/gcd.gds')
