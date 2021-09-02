import os
import subprocess
from tests.fixtures import test_wrapper

##################################
def test_gcd_infer_diesize():
    '''Test inferring diesize from density/aspectratio/margin arguments

    For now just tests that these flags don't break anything. TODO: is there a
    good way to test that the actual final floorplan is correct?
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/daily_tests/asic')] + '/examples/gcd/'

    # Run the build command.
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-target', 'freepdk45_asicflow',
                    '-asic_density', '10',
                    '-asic_aspectratio', '1',
                    '-asic_coremargin', '26.6',
                    '-constraint', gcd_ex_dir + '/gcd.sdc',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
