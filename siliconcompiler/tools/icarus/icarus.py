import os
import subprocess
import re
import sys
import siliconcompiler
import shutil

from siliconcompiler.schema_utils import schema_path


####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    Icarus is a verilog simulator with full support for Verilog
    IEEE-1364. Icarus can simulate synthesizable as well as
    behavioral Verilog.

    Documentation: http://iverilog.icarus.com

    Sources: https://github.com/steveicarus/iverilog.git

    Installation: https://github.com/steveicarus/iverilog.git

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step', 'sim')
    chip.set('arg','index', '<index>')
    setup_tool(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'icarus'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    chip.set('eda', tool, step, index, 'exe', 'iverilog', clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '-V', clobber=False)
    chip.set('eda', tool, step, index, 'version', '10.3', clobber=False)
    chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=False)


################################
#  Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    cmdlist = []

    # source files
    for value in chip.get('ydir'):
        cmdlist.append('-y ' + chip.find(value))
    for value in chip.get('vlib'):
        cmdlist.append('-v ' + chip.find(value))
    for value in chip.get('idir'):
        cmdlist.append('-I' + chip.find(value))
    for value in chip.get('define'):
        cmdlist.append('-D' + chip.find(value))
    for value in chip.get('cmdfile'):
        cmdlist.append('-f ' + chip.find(value))
    for value in chip.get('source'):
        cmdlist.append(chip.find(value))

    return cmdlist



################################
# Version Check
################################




def check_version(chip, version):
    ''' Tool specific version checking
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    required = chip.get('eda', 'icarus', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    return 0


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg("icarus.json")
