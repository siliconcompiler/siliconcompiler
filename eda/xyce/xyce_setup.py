import os

import siliconcompiler
from siliconcompiler.floorplan import *
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################
def setup_tool(chip, step):

     tool = 'xyce'

     chip.set('eda', tool, step, 'threads', '4')
     chip.set('eda', tool, step, 'copy', 'false')
     chip.set('eda', tool, step, 'format', 'cmdline')
     chip.set('eda', tool, step, 'vendor', tool)
     chip.set('eda', tool, step, 'exe', tool)




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
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_tool(chip, step='spice')
    # write out results
    chip.writecfg(output)
