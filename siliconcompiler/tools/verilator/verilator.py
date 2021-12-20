import os
import subprocess
import re
import sys
import siliconcompiler
import shutil
from siliconcompiler import utils

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    Verilator is a free and open-source software tool which converts
    Verilog (a hardware description language) to a cycle-accurate
    behavioral model in C++ or SystemC. It is restricted to modeling
    the synthesizable subset of Verilog and the generated models
    are cycle-accurate, 2-state, with synthesis (zero delay) semantics.
    As a consequence, the models typically offer higher performance
    than the more widely used event-driven simulators, which can
    process the entire Verilog language and model behavior within
    the clock cycle. Verilator is now used within academic research,
    open source projects and for commercial semiconductor
    development. It is part of the growing body of free EDA software.

    Documentation: https://verilator.org/guide/latest

    Sources: https://github.com/verilator/verilator

    Installation: https://verilator.org/guide/latest/install.html

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
    the dictionary settings. Static setings only.
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'verilator'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    chip.set('eda', tool, 'exe', 'verilator', clobber=False)
    chip.set('eda', tool, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, 'version', '4.028', clobber=False)
    chip.set('eda', tool, 'threads', step, index,  os.cpu_count(), clobber=False)

    # Options driven on a per step basis (use 'set' on first call!)
    chip.set('eda', tool, 'option', step, index,  '-sv', clobber=False)

    # Differentiate between import step and compilation
    if step in ['import', 'lint']:
        chip.add('eda', tool, 'option', step, index,  ['--lint-only','--debug'])
    elif (step == 'compile'):
        chip.add('eda', tool, 'option', step, index,  '--cc')
    else:
        chip.logger.error('Step %s not supported for verilator', step)
        sys.exit()

################################
#  Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returns list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    check_workdir = (step != 'import')

    cmdlist = []

    # source files
    for value in chip.find_files('ydir'):
        cmdlist.append('-y ' + value)
    for value in chip.find_files('vlib'):
        cmdlist.append('-v ' + value)
    for value in chip.find_files('idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('cmdfile'):
        cmdlist.append('-f ' + value)
    for value in chip.find_files('source'):
        cmdlist.append(value)

    #  make warnings non-fatal in relaxed mode
    if chip.get('relax'):
        cmdlist.append('-Wno-fatal')

    return cmdlist

################################
# Version Check
################################

def parse_version(stdout):
    # Verilator 4.104 2020-11-14 rev v4.104
    return stdout.split()[1]

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # post-process hack only needed for import step
    if step != 'import':
        return 0

    # Creating single file "pickle' synthesis handoff
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
        topmodule = chip.cfg['design']['value']

    # Moving pickled file to outputs
    os.rename("verilator.v", "outputs/" + topmodule + ".v")

    # Copy files from inputs to outputs
    utils.copytree("inputs", "outputs", dirs_exist_ok=True, link=True,
                   ignore=[f'{topmodule}.v', f'{topmodule}.pkg.json'])

    # Clean up
    shutil.rmtree('obj_dir')

    #Return 0 if successful
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip)
    # write out results
    chip.writecfg(output)
