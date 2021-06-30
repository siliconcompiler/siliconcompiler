import os
import siliconcompiler
from tests.fixtures import test_wrapper

##################################
def test_gcd_local():
    '''Basic CLI test: build the GCD example by running `sc` as a command-line app.
    '''

    # Find the OpenROAD examples directory under `third_party/`.
    or_ex_dir = os.path.abspath(__file__)
    or_ex_dir = or_ex_dir[:or_ex_dir.rfind('/tests/long_tests')]
    or_ex_dir += '/third_party/openroad/examples'

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    # Inserting value into configuration
    chip.add('source', or_ex_dir + '/gcd/gcd.v')
    chip.add('design', 'gcd')
    chip.add('clock', 'clock_name', 'pin', 'clk')
    chip.add('constraint', or_ex_dir + '/gcd/freepdk45.sdc')
    chip.set('target', "freepdk45")
    chip.set('asic', 'diesize', "0 0 100.13 100.8")
    chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
    chip.set_jobid()

    # Apply target PDK settings.
    chip.target()

    # Set verilator option to support this design's nonstandard metacomments.
    chip.cfg['flow']['import']['option']['value'].append('-Wfuture-')

    # Set a few last options, and run the job.
    chip.set('stop', 'export')
    chip.set('quiet', 'true')
    chip.run()

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.svg')
