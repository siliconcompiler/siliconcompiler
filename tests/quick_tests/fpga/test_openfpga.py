import os
import subprocess
# fixture automatically used when imported to create clean build dir
from tests.fixtures import test_wrapper

##################################
def test_openfpga():
    '''OpenFPGA bitstream generation test: build the and2 example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    openfpga_ex_dir = os.path.abspath(__file__)
    openfpga_ex_dir = openfpga_ex_dir[:openfpga_ex_dir.rfind('/tests/quick_tests/fpga')] + '/examples/and2_openfpga/'

    # Run the build command.
    subprocess.run(['sc',
                    openfpga_ex_dir + '/and2.v',
                    '-design', 'and2',
                    '-fpga_arch', openfpga_ex_dir + '/k6_frac_N10_40nm_openfpga.xml',
                    '-fpga_arch', openfpga_ex_dir + '/k6_frac_N10_40nm_vpr.xml', 
                    '-mode', 'fpga',
                    '-target', 'openfpga_fpgaflow'],
                   stdout = subprocess.DEVNULL)

    # Verify that a bitstream was generated
    assert os.path.isfile('build/and2/job1/apr/outputs/and2_fabric_bitstream.txt')
    assert os.path.isfile('build/and2/job1/apr/outputs/and2_fabric_bitstream.xml')
    assert os.path.isfile('build/and2/job1/apr/outputs/and2_fabric_independent_bitstream.xml')
