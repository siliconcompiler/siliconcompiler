import os
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

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step','import')
    chip.set('arg','index','0')
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
    chip.set('tool', tool, 'exe', exe)
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=1.13', clobber=False)
    chip.set('tool', tool, 'threads', step, index,  os.cpu_count(), clobber=False)

    # -parse is slow but ensures the SV code is valid
    # we might want an option to control when to enable this
    # or replace surelog with a SV linter for the validate step
    options = []
    options.append('-parse')

    # Wite back options tp cfg
    chip.add('tool', tool, 'option', step, index, options)

    # Input/Output requirements
    chip.add('tool', tool, 'output', step, index, chip.top() + '.v')

    # Schema requirements
    chip.add('tool', tool, 'require', step, index, ",".join(['input', 'verilog']))

    # We package SC wheels with a precompiled copy of Surelog installed to
    # tools/surelog/bin. If the user doesn't have Surelog installed on their
    # system path, set the path to the bundled copy in the schema.
    if shutil.which('surelog') is None:
        surelog_path = os.path.join(os.path.dirname(__file__), 'bin')
        chip.set('tool', tool, 'path', surelog_path, clobber=False)

    # Log file parsing
    chip.set('tool', tool, 'regex', step, index, 'warnings', r'^\[WRN:', clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', r'^\[(ERR|FTL|SNT):', clobber=False)

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

    cmdlist = []

    # source files
    for value in chip.find_files('option', 'ydir'):
        cmdlist.append('-y ' + value)
    for value in chip.find_files('option', 'vlib'):
        cmdlist.append('-v ' + value)
    for value in chip.find_files('option', 'idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('option', 'cmdfile'):
        cmdlist.append('-f ' + value)
    for value in chip.find_files('input', 'verilog'):
        cmdlist.append(value)

    cmdlist.append('-top ' + chip.top())
    # make sure we can find .sv files in ydirs
    # TODO: need to add libext
    cmdlist.append('+libext+.sv+.v')

    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param in chip.getkeys('option', 'param'):
        value = chip.get('option', 'param', param)
        cmdlist.append(f'-P{param}={value}')

    return cmdlist

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    step = chip.get('arg', 'step')

    if step != 'import':
        return 0

    # Look in slpp_all/file_elab.lst for list of Verilog files included in
    # design, read these and concatenate them into one pickled output file.
    with open('slpp_all/file_elab.lst', 'r') as filelist, \
            open(f'outputs/{chip.top()}.v', 'w') as outfile:
        for path in filelist.read().split('\n'):
            path = path.strip('"')
            if not path:
                # skip empty lines
                continue
            with open(path, 'r') as infile:
                outfile.write(infile.read())
            # in case end of file is missing a newline
            outfile.write('\n')

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("surelog.json")
