import os
import subprocess
import re
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
    chip.add('flow', step, 'refdir', '')
    chip.add('flow', step, 'script', '')
        
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

    options = chip.get('flow', step, 'option')
    
    if step == 'import':
        options.append('--lint-only --debug')
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
        options.append('-D ' + schema_path(value))

    for value in chip.cfg['cmdfile']['value']:
        options.append('-f ' + schema_path(value))
        
    for value in chip.cfg['source']['value']:
        options.append(schema_path(value))

    #Relax Linting
    supress_warnings = ['-Wno-UNOPTFLAT',
                        '-Wno-WIDTH',
                        '-Wno-SELRANGE',
                        '-Wno-WIDTH',
                        '-Wno-fatal']
    
    if schema_istrue(chip.cfg['relax']['value']):
        for value in supress_warnings:
            options.append(value)


    #Wite back options tp cfg
    chip.set('flow', step, 'option', options)
            
    return options

################################
# Pre and Post Run Commands
################################
def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''

    # filtering out debug garbage
    subprocess.run('egrep -h -v "\`begin_keywords" obj_dir/*.vpp > verilator.sv',
                   shell=True)
                   
    # setting top module of design
    modules = 0
    if(len(chip.cfg['design']['value']) < 1):
        with open("verilator.sv", "r") as open_file:
            for line in open_file:
                modmatch = re.match('^module\s+(\w+)', line)
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
    subprocess.run("cp verilator.sv " + "outputs/" + topmodule + ".sv",
                   shell=True)



