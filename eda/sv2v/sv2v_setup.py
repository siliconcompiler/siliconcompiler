import os
import subprocess
import re
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

################################
# Setup sv2v
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''
    chip.logger.debug("Setting up sv2v")
    
    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'copy', 'false')
    chip.add('flow', step, 'exe', 'sv2v')
    chip.add('flow', step, 'vendor', 'sv2v')
        
################################
# Set sv2v Runtime Options
################################

def setup_options(chip, step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''
    options = chip.set('flow', step, 'option',[])
    
    #Include cwd in search path
    options.append('--skip-preprocessor')

    for value in chip.cfg['source']['value']:
        options.append(schema_path(value))

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

    # setting top module of design
    modules = 0
    if(len(chip.cfg['design']['value']) < 1):
        with open("sv2v.log", "r") as open_file:
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

    subprocess.run("mv sv2v.log outputs/" + topmodule + ".sv", shell=True)
