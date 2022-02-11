import os
import subprocess
import re
import sys
import shutil

import siliconcompiler
from siliconcompiler import utils

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
    chip.set('design', '<design>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'surelog'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    exe = tool
    # Although Windows will find the binary even if the .exe suffix is omitted,
    # Surelog won't find the relative builtin.sv file unless we add it.
    if sys.platform.startswith('win32'):
        exe = f'{tool}.exe'

    # Standard Setup
    chip.set('eda', tool, 'exe', exe, clobber=False)
    chip.set('eda', tool, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, 'version', '1.14', clobber=False)
    chip.set('eda', tool, 'threads', step, index,  os.cpu_count(), clobber=False)

    # -parse is slow but ensures the SV code is valid
    # we might want an option to control when to enable this
    # or replace surelog with a SV linter for the validate step
    options = []
    options.append('-parse')

    # Wite back options tp cfg
    chip.add('eda', tool, 'option', step, index, options)

    # Input/Output requirements
    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.v')

    # Schema requirements
    chip.add('eda', tool, 'require', step, index, 'source')

    # We package SC wheels with a precompiled copy of Surelog installed to
    # tools/surelog/bin. If the user doesn't have Surelog installed on their
    # system path, set the path to the bundled copy in the schema.
    if shutil.which('surelog') is None:
        surelog_path = os.path.join(os.path.dirname(__file__), 'bin')
        chip.set('eda', tool, 'path', surelog_path, clobber=False)



def parse_version(stdout):
    # Surelog --version output looks like:
    # VERSION: 1.13
    # BUILT  : Nov 10 2021

    # grab version # by splitting on whitespace
    return stdout.split()[1]

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
    index = chip.get('arg', 'index')
    tool = 'surelog'

    if step != 'import':
        return 0

    # Log file parsing
    chip.set('eda', tool, 'regex', step, index, 'warnings', "WARNING")
    chip.set('eda', tool, 'regex', step, index, 'errors', "ERROR")

    # Output reprts for deep dive
    for metric in ('errors', 'warnings'):
        chip.set('eda', tool, 'report', step, index, metric, f"{step}.log")

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
