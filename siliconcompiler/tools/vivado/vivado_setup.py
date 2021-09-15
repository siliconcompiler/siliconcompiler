import os
import importlib
import re
import shutil
import sys
import siliconcompiler

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index, mode='batch'):
    '''
    '''

    # default tool settings, note, not additive!
    tool = 'vivado'
    vendor = 'xilinx'
    refdir = 'siliconcompiler/tools/' + tool
    script = 'compile.tcl'
    clobber = True

    # If the 'lock' bit is set, don't reconfigure.
    configured = chip.get('eda', tool, step, index, 'exe', field='lock')
    if configured and (configured != 'false'):
        chip.logger.warning('Tool already configured: ' + tool)
        return

    if mode == 'batch':
        clobber = True
        script = '/compile.tcl'
        option = "-mode batch -source"

    # General settings
    chip.set('eda', tool, step, index, 'vendor', vendor, clobber=clobber)
    chip.set('eda', tool, step, index, 'exe', tool, clobber=clobber)
    chip.set('eda', tool, step, index, 'refdir', refdir, clobber=clobber)
    chip.set('eda', tool, step, index, 'script', refdir + script, clobber=clobber)
    chip.set('eda', tool, step, index, 'vswitch', '-version', clobber=clobber)
    chip.set('eda', tool, step, index, 'version', '0', clobber=clobber)
    chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=clobber)
    chip.set('eda', tool, step, index, 'option', 'cmdline', option, clobber=clobber)

    # Set the 'lock' bit for this tool.
    chip.set('eda', tool, step, index, 'exe', 'true', field='lock')

################################
# Version Check
################################

def check_version(chip, step, index, version):
    ''' Tool specific version checking
    '''
    required = chip.get('eda', 'vivado', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0

################################
# Post_process (post executable)
################################

def post_process(chip, step, index):
     ''' Tool specific function to run after step execution
     '''

     #Return 0 if successful
     return 0
