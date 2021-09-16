import os
import subprocess
import re
import sys
import siliconcompiler
import shutil

from siliconcompiler.schema_utils import schema_path


####################################################################
# Make Docs
####################################################################

def make_docs():
    '''Verilator converts Verilog to a cycle accurate simulator model.

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

    Documentation:
    * https://github.com/chipsalliance/Surelog

    Installation instructions:
    * https://verilator.org/guide/latest/install.html

    Source Code:
    * https://verilator.org/guide/latest

    '''

    chip = siliconcompiler.Chip()
    setup_tool(chip,'lint','0')
    setup_tool(chip,'verilate','0')
    setup_tool(chip,'import','0')
    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'verilator'
    configured = chip.get('eda', tool, step, index, 'exe', field='lock')
    if configured and (configured != 'false'):
        chip.logger.warning('Tool already configured: ' + tool)
        return

    # Standard Setup
    chip.set('eda', tool, step, index, 'exe', 'verilator', clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, step, index, 'version', '4.211', clobber=False)
    chip.set('eda', tool, step, index, 'vendor', 'verilator', clobber=False)
    chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=False)

    # Options driven on a per step basis (use 'set' on first call!)
    chip.set('eda', tool, step, index, 'option', 'cmdline', '-sv', clobber=False)

    # Differentiate between import step and compilation
    if step in ['import', 'lint']:
        chip.add('eda', tool, step, index, 'option', 'cmdline', '--lint-only --debug')
    elif (step == 'sim'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '--cc')
    else:
        chip.logger.error('Step %s not supported for verilator', step)
        sys.exit()

    #Source Level Controls
    for value in chip.get('ydir'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-y ' + schema_path(value))
    for value in chip.get('vlib'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-v ' + schema_path(value))
    for value in chip.get('idir'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-I' + schema_path(value))
    for value in chip.get('define'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-D' + schema_path(value))
    for value in chip.get('cmdfile'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-f ' + schema_path(value))
    for value in chip.get('source'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', schema_path(value))

    #Make warnings non-fatal in relaxed mode
    if chip.get('relax'):
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-Wno-fatal')

################################
# Version Check
################################

def check_version(chip, step, index, version):
    ''' Tool specific version checking
    '''
    required = chip.get('eda', 'verilator', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0


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
