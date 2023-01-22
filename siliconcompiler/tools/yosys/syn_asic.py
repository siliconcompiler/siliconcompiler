
from .syn import setup as setup_syn
from .yosys import setup_asic

def setup(chip):
    ''' Helper method for configs specific to ASIC synthesis tasks.
    '''

    # Generic synthesis task setup.
    setup_syn(chip)

    # ASIC-specific setup.
    setup_asic(chip)
