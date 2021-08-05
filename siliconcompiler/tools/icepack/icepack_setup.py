import os
import importlib
import re
import sys
import siliconcompiler
from siliconcompiler.floorplan import *
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''
    tool = 'icepack'
    chip.set('eda', tool, step, 'vendor', tool)
    chip.set('eda', tool, step, 'exe', tool)
    chip.add('eda', tool, step, 'format', 'cmdline')
    chip.set('eda', tool, step, 'threads', '4')
    chip.set('eda', tool, step, 'copy', 'false')

    #Get default opptions from setup
    topmodule = chip.get('design')[-1]

    options = []
    options.append("inputs/" + topmodule + ".asc")
    options.append("outputs/" + topmodule + ".bit")
    chip.add('eda', tool, step, 'option', options)

################################
# Post_process (post executable)
################################
def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_tool(chip, step='bitstream')
    # write out results
    chip.writecfg(output)
