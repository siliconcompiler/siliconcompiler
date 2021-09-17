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
    setup_tool(chip,'<step>','0')
    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'icarus'

    if chip.get('eda', tool, step, index, 'exe', field='lock'):
        chip.logger.warning('Tool already configured: ' + tool)
        return

    # Standard Setup
    chip.set('eda', tool, step, index, 'exe', 'iverilog', clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '-V', clobber=False)
    chip.set('eda', tool, step, index, 'version', '10.3', clobber=False)
    chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=False)

    #Source Level Controls
    for value in chip.get('ydir'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-y ' + schema_path(value))
    for value in chip.get('vlib'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-v ' + schema_path(value))
    for value in chip.get('idir'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-I ' + schema_path(value))
    for value in chip.get('define'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-D ' + schema_path(value))
    for value in chip.get('cmdfile'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-f ' + schema_path(value))
    for value in chip.get('source'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', schema_path(value))


################################
# Version Check
################################

def check_version(chip, step, index, version):
    ''' Tool specific version checking
    '''
    required = chip.get('eda', 'icarus', step, index, 'version')
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

    return 0


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg("icarus.json")
