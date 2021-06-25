import os
import subprocess
import re
import sys
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

################################
# Setup GHDL
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''
    chip.logger.debug("Setting up GHDL")

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'copy', 'false')
    chip.add('flow', step, 'exe', 'ghdl')
    chip.add('flow', step, 'vendor', 'ghdl')

################################
# Set GHDL Runtime Options
################################

def setup_options(chip, step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    options = chip.set('flow', step, 'option', [])

    options.append('--synth')
    options.append('--std=08')
    options.append('--no-formal')
    options.append('--out=verilog')

    for value in chip.cfg['define']['value']:
        options.append('-g' + schema_path(value))

    for value in chip.cfg['source']['value']:
        options.append(schema_path(value))

    if len(chip.cfg['design']['value']) < 1:
            chip.logger.error('No top module set')
            return

    topmodule = chip.cfg['design']['value'][-1]

    options.append('-e ' + topmodule)

    # Write back options to cfg
    chip.set('flow', step, 'option', options)

    return options

################################
# Pre and Post Run Commands
################################
def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''

    topmodule = chip.cfg['design']['value'][-1]
    subprocess.run("cp ghdl.log outputs/" + topmodule + ".v", shell=True)
