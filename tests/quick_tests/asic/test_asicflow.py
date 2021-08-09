import os
import siliconcompiler
from tests.fixtures import test_wrapper

##################################
def test_gcd_local_py():
    '''Basic Python API test: build the GCD example using only Python code.
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/quick_tests/asic')] + '/examples/gcd/'

    # Inserting value into configuration
    chip.add('source', gcd_ex_dir + 'gcd.v')
    chip.add('design', 'gcd')
    chip.add('clock', 'clock_name', 'pin', 'clk')
    chip.add('constraint', gcd_ex_dir + 'gcd.sdc')
    chip.set('target', "freepdk45_asicflow")
    chip.set('asic', 'diesize', "0 0 100.13 100.8")
    chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
    chip.set_jobid()

    chip.target()

    chip.set('stop', 'export')
    chip.set('quiet', 'true')
    chip.set('relax', 'true')

    # Run the chip's build process synchronously.
    chip.run()

    # (Printing the summary makes it harder to see other test case results.)
    #chip.summary()

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
