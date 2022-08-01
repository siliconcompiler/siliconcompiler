import os

import siliconcompiler

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

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step', 'run')
    chip.set('arg','index', '<index>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'icarus'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    design = chip.top()

    # Standard Setup
    chip.set('tool', tool, 'exe', 'iverilog')
    chip.set('tool', tool, 'vswitch', '-V')
    chip.set('tool', tool, 'version', '>=10.3', clobber=False)
    chip.set('tool', tool, 'threads', step, index, os.cpu_count(), clobber=False)

    if step == 'compile':
        chip.set('tool', tool, 'option', step, index,'-o outputs/'+design+'.vvp')
    elif step == 'run':
        chip.set('tool', tool, 'option', step, index, '')
    else:
        chip.logger.error(f"Step '{step}' not supported in Icarus tool")

    # Schema requirements
    chip.add('tool', tool, 'require', step, index, 'input,verilog')

################################
#  Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    cmdlist = []

    # source files
    for value in chip.find_files('option','ydir'):
        cmdlist.append('-y ' + value)
    for value in chip.find_files('option','vlib'):
        cmdlist.append('-v ' + value)
    for value in chip.find_files('option','idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('option','define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('option','cmdfile'):
        cmdlist.append('-f ' + value)
    for value in chip.find_files('input', 'verilog'):
        cmdlist.append(value)

    return cmdlist

################################
# Version Check
################################

def parse_version(stdout):
    # First line: Icarus Verilog version 10.1 (stable) ()
    return stdout.split()[3]

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("icarus.json")
