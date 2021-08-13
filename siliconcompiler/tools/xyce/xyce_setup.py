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
