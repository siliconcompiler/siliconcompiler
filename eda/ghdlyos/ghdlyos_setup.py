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
    chip.logger.debug("Setting up GHDL Yosys")

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'copy', 'false')
    chip.add('flow', step, 'exe', 'yosys')
    chip.add('flow', step, 'vendor', 'ghdlyos')

################################
# Set GHDL Runtime Options
################################

def setup_options(chip, step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    options = chip.set('flow', step, 'option', [])

    options.append('-m ghdl')
    options.append('-p \'ghdl')

    options.append('--std=08')
    options.append('--no-formal')

    for value in chip.cfg['define']['value']:
        options.append('-g' + schema_path(value))

    for value in chip.cfg['source']['value']:
        if value.endswith('.vhd') or value.endswith('.vhdl'):
            options.append(schema_path(value))

    modules = ""
    try:
        with open("inputs/undefined.morty", "r") as undefined_file:
            modules = undefined_file.read().strip()
    except FileNotFoundError:
        if len(chip.cfg['design']['value']) < 1:
            chip.logger.error('No top module set')
            return
        modules = chip.cfg['design']['value'][-1]

    options.append('-e ' + modules)

    options.append('; write_ilang ghdl.ilang\'')

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
    subprocess.run("cp ghdl.ilang " + "outputs/" + topmodule + ".ilang",
                   shell=True)
    subprocess.run("cp inputs/" + topmodule + ".v" + " outputs/", shell=True)
