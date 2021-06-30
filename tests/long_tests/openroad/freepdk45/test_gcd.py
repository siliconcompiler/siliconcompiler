import os
import subprocess
from tests.fixtures import test_wrapper

##################################
def test_gcd_local():
    '''Basic CLI test: build the GCD example by running `sc` as a command-line app.
    '''

    # Find the OpenROAD examples directory under `third_party/`.
    or_ex_dir = os.path.abspath(__file__)
    or_ex_dir = or_ex_dir[:or_ex_dir.rfind('/tests/long_tests')]
    or_ex_dir += '/third_party/openroad/examples'

    # Run the basic `sc` flow.
    subprocess.run(['sc',
                    or_ex_dir + '/gcd/gcd.v',
                    '-design', 'gcd',
                    '-target', 'freepdk45',
                    '-asic_diesize', '0 0 100.13 100.8',
                    '-asic_coresize', '10.07 11.2 90.25 91',
                    '-constraint', or_ex_dir + '/gcd/freepdk45.sdc',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.svg')
