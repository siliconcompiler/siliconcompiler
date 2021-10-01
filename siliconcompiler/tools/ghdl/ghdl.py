import os
import subprocess
import re
import sys
import json
import siliconcompiler

#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''
    GHDL is an open-source analyzer, compiler, simulator and
    (experimental) synthesizer for VHDL. It allows you to analyse
    and elaborate sources for generating machine code from your design.
    Native program execution is the only way for high speed simulation.

    Documentation: https://ghdl.readthedocs.io/en/latest

    Sources: https://github.com/ghdl/ghdl

    Installation: https://github.com/ghdl/ghdl

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','import')
    chip.set('arg','index','<index>')
    setup_tool(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # Standard Setup
    tool = 'ghdl'
    clobber = False

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    chip.set('eda', tool, step, index, 'threads', '4', clobber=clobber)
    chip.set('eda', tool, step, index, 'copy', 'false', clobber=clobber)
    chip.set('eda', tool, step, index, 'exe', 'ghdl', clobber=clobber)
    chip.set('eda', tool, step, index, 'version', '0.0', clobber=clobber)

################################
#  Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    options = []

    # Synthesize inputs and output Verilog netlist
    options.append('--synth')
    options.append('--out=verilog')

    # Add sources
    for value in chip.get('source'):
        options.append(chip.find_file(value))

    # Set top module
    design = chip.get('design')
    options.append('-e')
    options.append(design)

    # ghdl dumps output to stdout, so have to insert redirection as part of
    # command
    options.append('>')
    options.append(f'outputs/{design}.v')

    return options

################################
# Version Check
################################

def check_version(chip, version):
    ''' Tool specific version checking
    '''
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    required = chip.get('eda', 'ghdl', step, index, 'version')
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

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='import', index='0')
    # write out results
    chip.writecfg(output)
