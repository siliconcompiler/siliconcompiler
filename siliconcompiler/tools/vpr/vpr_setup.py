
import os

import siliconcompiler
from siliconcompiler.floorplan import *
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################
def setup_tool(chip, step, index):

     tool = 'vpr'
     refdir = 'siliconcompiler/tools/vpr'

     chip.set('eda', tool, step, index, 'threads', '4')
     chip.set('eda', tool, step, index, 'copy', 'false')
     chip.set('eda', tool, step, index, 'format', 'cmdline')
     chip.set('eda', tool, step, index, 'vendor', tool)
     chip.set('eda', tool, step, index, 'exe', tool)

     topmodule = chip.get('design')
     blif = "inputs/" + topmodule + ".blif"

     options = []
     for arch in chip.get('fpga','arch'):
          options.append(arch)

     options.append(blif)

     chip.add('eda', tool, step, index, 'option', 'cmdline', options)

################################
# Post_process (post executable)
################################

def post_process(chip, step ):
    ''' Tool specific function to run after step execution
    '''

    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_tool(chip, step='apr', index='0')
    # write out results
    chip.writecfg(output)
