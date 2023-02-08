
from siliconcompiler.tools.yosys.yosys import syn_setup, create_vpr_lib, setup_fpga, syn_post_process

def setup(chip):
    ''' Helper method for configs specific to FPGA synthesis tasks.
    '''

    # Generic synthesis task setup.
    syn_setup(chip)

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

##################################################
def post_process(chip):
    syn_post_process(chip)
