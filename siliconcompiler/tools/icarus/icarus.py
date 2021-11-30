import os
import subprocess
import re
import sys
import siliconcompiler
import shutil

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
    design = chip.get('design')

    # Standard Setup
    chip.set('eda', tool, step, index, 'exe', 'iverilog', clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '-V', clobber=False)
    chip.set('eda', tool, step, index, 'version', '10.3', clobber=False)
    chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=False)

    if step == 'compile':
        chip.set('eda', tool, step, index,'option','-o outputs/'+design+'.vvp')
    elif step == 'run':
        chip.set('eda', tool, step, index,'option','')
    else:
        chip.logger.error(f"Step '{step}' not supported in Icarus tool")

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
    for value in chip.find_files('ydir'):
        cmdlist.append('-y ' + value)
    for value in chip.find_files('vlib'):
        cmdlist.append('-v ' + value)
    for value in chip.find_files('idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('cmdfile'):
        cmdlist.append('-f ' + value)
    for value in chip.find_files('source'):
        cmdlist.append(value)

    return cmdlist

################################
# Version Check
################################

def parse_version(stdout):
    # First line: Icarus Verilog version 10.1 (stable) ()
    return stdout.split()[3]

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
