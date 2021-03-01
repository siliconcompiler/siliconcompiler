import os
import subprocess

################################
# Setup Verilator
################################

def setup_tool(chip, stage):
    ''' Sets up default settings on a per stage basis
    '''
    chip.add('tool', stage, 'threads', '4')
    chip.add('tool', stage, 'format', 'cmdline')
    chip.add('tool', stage, 'copy', 'false')
    chip.add('tool', stage, 'exe', 'verilator')
    chip.add('tool', stage, 'vendor', 'verilator')
    chip.add('tool', stage, 'refdir', '')
    chip.add('tool', stage, 'script', '')
    chip.add('tool', stage, 'opt', '--lint-only --debug')
  
################################
# Set Verilator Runtime Options
################################

def setup_options(chip,stage):
    ''' Per tool/stage function that returns a dynamic options string based on
    the dictionary settings.
    '''

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
    ''' Tool specific function to run before stage execution
    '''
    pass

def post_process(chip,stage):
    ''' Tool specific function to run after stage execution
    '''

    # filtering out debug garbage
    subprocess.run('grep -h -v \`begin_keywords obj_dir/*.vpp > verilator.v',
                   shell=True)
                   
    # setting top module of design
    modules = 0
    if(len(chip.cfg['design']['value']) < 1):
        with open("verilator.v", "r") as open_file:
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
    subprocess.run("cp verilator.v " + "outputs/" + topmodule + ".v",
                   shell=True)



