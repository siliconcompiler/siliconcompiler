
from .syn import setup as setup_syn
from .yosys import setup_asic, prepare_synthesis_libraries, create_abc_synthesis_constraints

def setup(chip):
    ''' Helper method for configs specific to ASIC synthesis tasks.
    '''

    # Generic synthesis task setup.
    setup_syn(chip)

    # ASIC-specific setup.
    setup_asic(chip)

##################################################
def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    prepare_synthesis_libraries(chip)
    create_abc_synthesis_constraints(chip)
    return
