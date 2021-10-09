import os
import subprocess
import re
import sys
import shutil

import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    Surelog is a SystemVerilog pre-processor, parser, elaborator,
    and UHDM compiler that provdes IEEE design and testbench
    C/C++ VPI and a Python AST API.

    Documentation: https://github.com/chipsalliance/Surelog

    Sources: https://github.com/chipsalliance/Surelog

    Installation: https://github.com/chipsalliance/Surelog

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','import')
    chip.set('arg','index','0')
    setup_tool(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'surelog'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    chip.set('eda', tool, step, index, 'exe', tool, clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, step, index, 'version', '0.0', clobber=False)
    chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=False)

    # -parse is slow but ensures the SV code is valid
    # we might want an option to control when to enable this
    # or replace surelog with a SV linter for the validate step
    options = []
    options.append('-parse')

    # Wite back options tp cfg
    chip.add('eda', tool, step, index, 'option', 'cmdline', options)

def check_version(chip, version):
    pass

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
        cmdlist.append('-y ' + chip.find_file(value))
    for value in chip.get('vlib'):
        cmdlist.append('-v ' + chip.find_file(value))
    for value in chip.get('idir'):
        cmdlist.append('-I' + chip.find_file(value))
    for value in chip.get('define'):
        cmdlist.append('-D' + value)
    for value in chip.get('cmdfile'):
        cmdlist.append('-f ' + chip.find_file(value))
    for value in chip.get('source'):
        cmdlist.append(chip.find_file(value))

    cmdlist.append('-top ' + chip.get('design'))
    # make sure we can find .sv files in ydirs
    cmdlist.append('+libext+.sv')

    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param in chip.getkeys('param'):
        value = chip.get('param', param)
        cmdlist.append(f'-P{param}={value}')

    return cmdlist

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    design = chip.get('design')
    step = chip.get('arg', 'step')

    if step != 'import':
        return 0

    # Copy files from inputs to outputs. Need to do this before pickling since
    # we may otherwise overwrite the pickled file with one of the Verilog
    # sources.
    shutil.copytree("inputs", "outputs", dirs_exist_ok=True)

    # Look in slpp_all/file_elab.lst for list of Verilog files included in
    # design, read these and concatenate them into one pickled output file.
    with open('slpp_all/file_elab.lst', 'r') as filelist, \
            open(f'outputs/{design}.v', 'w') as outfile:
        for path in filelist.read().split('\n'):
            if not path:
                # skip empty lines
                continue
            with open(path, 'r') as infile:
                outfile.write(infile.read())
            # in case end of file is missing a newline
            outfile.write('\n')

    # Clean up
    shutil.rmtree('slpp_all')

    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='lint', index='0')
    # write out results
    chip.writecfg(output)
