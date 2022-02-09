import os
import importlib
import re
import sys
import siliconcompiler

#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''
    Icepack converts an ASCII bitstream file to a .bin file for the
    ICE40 FPGA.

    Documentation: http://www.clifford.at/icestorm

    Sources: https://github.com/YosysHQ/icestorm

    Installation: https://github.com/YosysHQ/icestorm

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','bitstream')
    chip.set('arg','index','<index>')
    setup(chip)
    return chip


################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''
    tool = 'icepack'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    clobber = False
    chip.set('eda', tool, 'exe', tool, clobber=clobber)
    chip.set('eda', tool, 'option', step, index, "", clobber=clobber)

    design = chip.get('design')
    chip.set('eda', tool, 'input', step, index, f'{design}.asc')
    chip.set('eda', tool, 'output', step, index, f'{design}.bit')

################################
#  Custom runtime options
################################

def runtime_options(chip):
    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    topmodule = chip.get('design')

    cmdlist = []
    cmdlist.append("inputs/" + topmodule + ".asc")
    cmdlist.append("outputs/" + topmodule + ".bit")

    return cmdlist

################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='bitstream', index='0')
    # write out results
    chip.writecfg(output)
