import os
import siliconcompiler
from tests.fixtures import test_wrapper

##################################
def test_gcd_local_py():
    '''Basic Python API test: build the GCD example using only Python code.
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    # Inserting value into configuration
    chip.add('source', 'examples/gcd/gcd.v')
    chip.add('design', 'gcd')
    chip.add('clock', 'clock_name', 'pin', 'clk')
    chip.add('constraint', "examples/gcd/constraint.sdc")
    chip.set('target', "freepdk45")
    chip.set('asic', 'diesize', "0 0 100.13 100.8")
    chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
    chip.set_jobid()

    chip.target()

    chip.set('stop', 'export')
    chip.set('quiet', 'true')

    # Run the chip's build process synchronously.
    chip.run()

    # (Printing the summary makes it harder to see other test case results.)
    #chip.summary()

    # Verify that a GDS file was generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
