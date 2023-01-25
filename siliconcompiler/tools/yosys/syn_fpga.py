
from .syn import setup as setup_syn
from .yosys import create_vpr_lib, setup_fpga

def setup(chip):
    ''' Helper method for configs specific to FPGA synthesis tasks.
    '''

    # Generic synthesis task setup.
    setup_syn(chip)

    # FPGA-specific setup.
    setup_fpga(chip)

##################################################
def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    # copy the VPR library to the yosys input directory and render the placeholders
    if chip.get('fpga', 'arch'):
        create_vpr_lib(chip)
        return
