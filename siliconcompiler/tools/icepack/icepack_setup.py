import os
import importlib
import re
import sys
import siliconcompiler

#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''Icepack converts an ASCII file to an ICE40 .bin file

    Documentation:
    * http://www.clifford.at/icestorm

    Source code:

    * https://github.com/YosysHQ/icestorm

    Build instructions:

    git clone https://github.com/YosysHQ/icestorm.git icestorm
    cd icestorm
    make -j$(nproc)
    sudo make install

    '''

    chip = siliconcompiler.Chip()
    setup_tool(chip,'bitstream','<index>')
    return chip


################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Sets up default settings on a per step basis
    '''
    tool = 'icepack'
    chip.set('eda', tool, step, index, 'vendor', tool)
    chip.set('eda', tool, step, index, 'exe', tool)
    chip.set('eda', tool, step, index, 'version', '0')

    #Get default opptions from setup
    topmodule = chip.get('design')

    options = []
    options.append("inputs/" + topmodule + ".asc")
    options.append("outputs/" + topmodule + ".bit")
    chip.add('eda', tool, step, index, 'option', 'cmdline', options)

################################
# Post_process (post executable)
################################
def post_process(chip, step, index):
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
