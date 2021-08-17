import os
import siliconcompiler
from tests.fixtures import test_wrapper

##################################
def test_k4n4_openfpga_py():
    '''Basic Python API test: build a basic 4-LUT FPGA using OpenFPGA
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    k4n4_ex_dir = os.path.abspath(__file__)
    k4n4_ex_dir = k4n4_ex_dir[:k4n4_ex_dir.rfind('/tests/quick_tests/asic')] + '/examples/k4n4_tileableio/'
    top_module = 'fpga_top'

    # Inserting value into configuration
    chip.add('source', k4n4_ex_dir + '/config/task.conf')
    chip.add('design', top_module)
    chip.add('clock', 'clock_name', 'pin', 'clk')
    chip.add('clock', 'clock_name', 'pin', 'prog_clk')
    chip.set('target', "freepdk45_openfpgaflow")
    chip.set('asic', 'diesize', "0 0 100.13 100.8")
    chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
    chip.set_jobid()
    chip.target()
    chip.set('quiet', 'true')
    chip.set('relax', 'true')

    # Run the chip's build process synchronously.
    chip.run()

    # (Printing the summary makes it harder to see other test case results.)
    #chip.summary()

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile(f'build/{top_module}/job0/export0/outputs/{top_module}.gds')
