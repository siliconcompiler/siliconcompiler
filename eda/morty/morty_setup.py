import os
import subprocess
import re
import sys
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''
    chip.logger.debug("Setting up Morty")

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'copy', 'false')
    chip.add('flow', step, 'exe', 'morty')
    chip.add('flow', step, 'vendor', 'morty')

def setup_options(chip, step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    options = chip.set('flow', step, 'option', [])

    options.append('-o morty.v')
    options.append('--write-undefined')

    for value in chip.cfg['ydir']['value']:
        options.append('--library-dir ' + schema_path(value))

    for value in chip.cfg['vlib']['value']:
        options.append('--library-file ' + schema_path(value))

    for value in chip.cfg['idir']['value']:
        options.append('-I ' + schema_path(value))

    for value in chip.cfg['define']['value']:
        options.append('-D ' + schema_path(value))

    for value in chip.cfg['source']['value']:
        if value.endswith('.v') or value.endswith('.vh') or \
            value.endswith('.sv') or value.endswith('.svh'):
            options.append(schema_path(value))

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

    # setting top module of design
    modules = 0
    if len(chip.cfg['design']['value']) < 1:
        with open("morty.v", "r") as open_file:
            for line in open_file:
                modmatch = re.match(r'^module\s+(\w+)', line)
                if modmatch:
                    modules = modules + 1
                    topmodule = modmatch.group(1)
        # Only setting design when possible
        if (modules > 1) & (chip.cfg['design']['value'] == ""):
            chip.logger.error('Multiple modules found during import, \
            but sc_design was not set')
            sys.exit()
        else:
            chip.logger.info('Setting design (topmodule) to %s', topmodule)
            chip.cfg['design']['value'].append(topmodule)
    else:
        topmodule = chip.cfg['design']['value'][-1]

    # Creating file for handoff to synthesis
    subprocess.run("cp morty.v " + "outputs/" + topmodule + ".v", shell=True)
    subprocess.run("cp undefined.morty " + "outputs/", shell=True)
