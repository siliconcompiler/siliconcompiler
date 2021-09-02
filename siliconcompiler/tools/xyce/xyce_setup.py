import os

import siliconcompiler
from siliconcompiler.floorplan import *

################################
# Setup Tool (pre executable)
################################
def setup_tool(chip, step, index):

     chip.set('eda', tool, step, index, 'threads', '4')
     chip.set('eda', tool, step, index, 'copy', 'false')
     chip.set('eda', tool, step, index, 'vendor', 'xyce')
     chip.set('eda', tool, step, index, 'exe', 'xyce')
     chip.set('eda', tool, step, index, 'version', '0.0')

################################
# Post_process (post executable)
################################
def post_process(chip, step):
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
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='spice', index='0')
    # write out results
    chip.writecfg(output)
