import os
import subprocess
import re
import sys


import siliconcompiler
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    chip.logger.debug("Setting up sv2v")


    tool = 'sv2v'

    chip.set('eda', tool, step, 'threads', '4')
    chip.set('eda', tool, step, 'format', 'cmdline')
    chip.set('eda', tool, step, 'copy', 'false')
    chip.set('eda', tool, step, 'exe', tool)
    chip.set('eda', tool, step, 'vendor', tool)

    # Include cwd in search path
    chip.set('eda', tool, step, 'option', '-I../../../')

    for value in chip.cfg['idir']['value']:
        chip.add('eda', tool, step, 'option', '-I' + schema_path(value))

    for value in chip.cfg['define']['value']:
        chip.add('eda', tool, step, 'option', '-D ' + schema_path(value))

 
    # since this step should run after import, the top design module should be
    # set and we can read the pickled Verilog without accessing the original
    # sources
    topmodule = chip.cfg['design']['value'][-1]
    chip.add('eda', tool, step, 'option', "inputs/" + topmodule + ".v")
    chip.add('eda', tool, step, 'option', "--write=outputs/" + topmodule + ".v")

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
    setup_tool(chip, step='transalate')
    # write out results
    chip.writecfg(output)
