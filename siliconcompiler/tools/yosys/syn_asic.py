
from siliconcompiler.tools.yosys.yosys import syn_setup, setup_asic, prepare_synthesis_libraries, create_abc_synthesis_constraints, syn_post_process

def make_docs(chip):
    chip.load_target("asap7_demo")

def setup(chip):
    ''' Helper method for configs specific to ASIC synthesis tasks.
    '''

    # Generic synthesis task setup.
    syn_setup(chip)

    # ASIC-specific setup.
    setup_asic(chip)

##################################################
def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    prepare_synthesis_libraries(chip)
    create_abc_synthesis_constraints(chip)
    return

def post_process(chip):
    syn_post_process(chip)