import os
import subprocess
import re
import sys
import siliconcompiler
import shutil

from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # Standard Setup
    tool = 'verilator'
    refdir = 'siliconcompiler/tools/verilator'
    chip.set('eda', 'format',  tool, step, index, 'cmdline')
    chip.set('eda', 'exe',     tool, step, index, 'verilator')
    chip.set('eda', 'vswitch', tool, step, index, '--version')
    chip.set('eda', 'version', tool, step, index, '4.211')
    chip.set('eda', 'vendor',  tool, step, index, 'verilator')
    chip.set('eda', 'refdir',  tool, step, index, refdir)
    chip.set('eda', 'threads', tool, step, index, 4)

    # Options driven on a per step basis (use 'set' on first call!)
    chip.set('eda', 'option', tool, step, index, 'cmdline', '-sv')

    # Differentiate between import step and compilation
    if step in ['import', 'lint']:
        chip.add('eda', 'option', tool, step, index, 'cmdline', '--lint-only --debug')
    elif (step == 'sim'):
        chip.add('eda', 'option', tool, step, index, 'cmdline', '--cc')
    else:
        chip.logger.error('Step %s not supported for verilator', step)
        sys.exit()

    #Include cwd in search path (verilator default)
    chip.add('eda', 'option', tool, step, index, 'cmdline', '-I../../../')

    #Source Level Controls
    for value in chip.get('ydir'):
        chip.add('eda', 'option', tool, step, index, 'cmdline', '-y ' + schema_path(value))
    for value in chip.get('vlib'):
        chip.add('eda', 'option', tool, step, index, 'cmdline', '-v ' + schema_path(value))
    for value in chip.get('idir'):
        chip.add('eda', 'option', tool, step, index, 'cmdline', '-I' + schema_path(value))
    for value in chip.get('define'):
        chip.add('eda', 'option', tool, step, index, 'cmdline', '-D' + schema_path(value))
    for value in chip.get('cmdfile'):
        chip.add('eda', 'option', tool, step, index, 'cmdline', '-f ' + schema_path(value))
    for value in chip.get('source'):
        chip.add('eda', 'option', tool, step, index, 'cmdline', schema_path(value))

    #Make warnings non-fatal in relaxed mode
    if chip.get('relax'):
        chip.add('eda', 'option', tool, step, index, 'cmdline', '-Wno-fatal')

################################
# Post_process (post executable)
################################

def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''

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

    # Copy files from inputs to outputs
    shutil.copytree("inputs", "outputs", dirs_exist_ok=True)

    # Moving pickled file to outputs
    os.rename("verilator.v", "outputs/" + topmodule + ".v")

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
    setup_tool(chip, step='import', index='0')
    # write out results
    chip.writecfg(output)
