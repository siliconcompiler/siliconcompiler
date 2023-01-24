
from .syn import setup as setup_syn
from .yosys import setup_fpga

def setup(chip):
    ''' Helper method for configs specific to FPGA synthesis tasks.
    '''

    # Generic synthesis task setup.
    setup_syn(chip)

    # FPGA-specific setup.
    setup_fpga(chip)
