
from siliconcompiler.tools.yosys.yosys import syn_setup, setup_asic, prepare_synthesis_libraries, create_abc_synthesis_constraints, syn_post_process
import siliconcompiler

def make_docs():
    chip = siliconcompiler.Chip('<design>')
    chip.load_target('freepdk45_demo')
    chip.set('arg', 'step', '<step>')
    chip.set('arg', 'index', '<index>')
    chip.set('flowgraph', chip.get('option', 'flow'), '<step>', '<index>', 'tool', 'yosys')
    chip.set('flowgraph', chip.get('option', 'flow'), '<step>', '<index>', 'task', 'syn_asic')
    setup(chip)
    return chip

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