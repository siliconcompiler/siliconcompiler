import os
import subprocess
import re
import sys
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

################################
# Setup Verilator
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''
    chip.logger.debug("Setting up Verilator")

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'copy', 'false')
    chip.add('flow', step, 'exe', 'verilator')
    chip.add('flow', step, 'vendor', 'verilator')

################################
# Set Verilator Runtime Options
################################

def setup_options(chip, step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    #Get default opptions from setup
    #TODO: add options for:
    #sc/scc
    #clk
    #-stats --stats-vars -profile-cfuncs
    #-trace --trace-structs
    #-CFLAGS
    #-O3
    #

    options = chip.set('flow', step, 'option', [])

    if step == 'import':
        options.append('--lint-only --debug -sv')
    else:
        options.append('--cc')

    #Include cwd in search path (verilator default)
    options.append('-I' + "../../../")

    #Source Level Controls

    for value in chip.cfg['ydir']['value']:
        options.append('-y ' + schema_path(value))

    for value in chip.cfg['vlib']['value']:
        options.append('-v ' + schema_path(value))

    for value in chip.cfg['idir']['value']:
        options.append('-I' + schema_path(value))

    for value in chip.cfg['define']['value']:
        options.append('-D' + schema_path(value))

    for value in chip.cfg['cmdfile']['value']:
        options.append('-f ' + schema_path(value))

    for value in chip.cfg['source']['value']:
        options.append(schema_path(value))

    #Make warnings non-fatal in relaxed mode
    if schema_istrue(chip.cfg['relax']['value']):
        options.append('-Wno-fatal')

    #Wite back options tp cfg
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

    #Filtering our module not found errors
    total_errors=0
    error=0    
    with open("verilator.log", "r") as open_file:
        for line in open_file:
            errmatch = re.match(r'^%Error\:.*Cannot find file containing module', line)
            exitmatch = re.match(r'^%Error\:\s+Exiting due to (\d+) error', line)
            if errmatch:
                total_errors = total_errors + 1
            elif exitmatch:
                if int(exitmatch.group(1)) == total_errors:
                    error=0
                else:
                    error=1

    # filtering out debug garbage
    subprocess.run('egrep -h -v "\\`begin_keywords" obj_dir/*.vpp > verilator.v',
                   shell=True)

    # setting top module of design
    modules = 0
    if len(chip.cfg['design']['value']) < 1:
        with open("verilator.v", "r") as open_file:
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
    subprocess.run("cp verilator.v " + "outputs/" + topmodule + ".v",
                   shell=True)

    #return error code
    return error

