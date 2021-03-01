import os
import siliconcompiler as sc


################################
# Setup Verilator
################################

def setup_tool(chip, stage):
     
    chip.add('tool', stage, 'threads', '4')
    chip.add('tool', stage, 'format', 'tcl')
    chip.add('tool', stage, 'copy', 'false')
    chip.add('tool', stage, 'exe', 'verilator')
    chip.add('tool', stage, 'vendor', 'verilator')
    chip.add('tool', stage, 'opt', '--lint-only --debug')
  
################################
# Set Verilator Runtime Options
################################

def setup_options(chip,stage):

    #Get default opptions from setup
    options = chip.get('tool', stage, 'opt')

    #Include cwd in search path (verilator default)

    cwd = os.getcwd()    
    options.append('-I' + cwd + "/../../../")

    for value in chip.cfg['ydir']['value']:
        options.append('-y ' + value)

    for value in chip.cfg['vlib']['value']:
        options.append('-v ' + value)                    

    for value in chip.cfg['idir']['value']:
        options.append('-I' + value)

    for value in chip.cfg['define']['value']:
        options.append('-D ' + value)

    for value in chip.cfg['source']['value']:
        options.append(value)

    return options

################################
# Pre and Post Run Commands
################################
def pre_process(chip,stage):
    pass

def post_process(chip,stage):
    pass



