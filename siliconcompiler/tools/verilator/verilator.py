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

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step','import')
    chip.set('arg','index','<index>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings. Static setings only.
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'verilator'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    chip.set('tool', tool, 'exe', 'verilator', clobber=False)
    chip.set('tool', tool, 'vswitch', '--version', clobber=False)
    chip.set('tool', tool, 'version', '>=4.028', clobber=False)
    chip.set('tool', tool, 'threads', step, index,  os.cpu_count(), clobber=False)

    # Options driven on a per step basis (use 'set' on first call!)
    chip.set('tool', tool, 'option', step, index,  '-sv', clobber=False)

    # Differentiate between import step and compilation
    if step in ['import', 'lint']:
        chip.add('tool', tool, 'option', step, index,  ['--lint-only', '--debug'])
    elif (step == 'compile'):
        chip.add('tool', tool, 'option', step, index,  '--cc')
    else:
        chip.logger.error(f'Step {step} not supported for verilator')
        raise siliconcompiler.SiliconCompilerError(f'Step {step} not supported for verilator')

    if step == 'import':
        design = chip.get('design')
        chip.set('tool', tool, 'output', step, index, f'{design}.v')

    # Schema requirements
    chip.add('tool', tool, 'require', step, index, ",".join(['input', 'verilog']))
    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'regex', step, index, 'warnings', "\%Warning", clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', "\%Error", clobber=False)

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
    for value in chip.find_files('option', 'ydir'):
        cmdlist.append('-y ' + value)
    for value in chip.find_files('option', 'vlib'):
        cmdlist.append('-v ' + value)
    for value in chip.find_files('option', 'idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('option', 'cmdfile'):
        cmdlist.append('-f ' + value)
    for value in chip.find_files('input', 'verilog'):
        cmdlist.append(value)

    #  make warnings non-fatal in relaxed mode
    if chip.get('option', 'relax'):
        cmdlist.extend(['-Wno-fatal', '-Wno-UNOPTFLAT'])

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
    logfile = f"{step}.log"

    # post-process hack to collect vpp files
    if step in ['import', 'lint']:
        # Creating single file "pickle' synthesis handoff
        subprocess.run('egrep -h -v "\\`begin_keywords" obj_dir/*.vpp > verilator.v',
                       shell=True)

        # Moving pickled file to outputs
        os.rename("verilator.v", f"outputs/{chip.design}.v")

        # Clean up
        shutil.rmtree('obj_dir')


    # check log file for errors and statistics
    errors = 0
    warnings = 0
    with open(logfile) as f:
        for line in f:
            warnmatch = re.match(r'^\%Warning', line)
            errmatch = re.match(r'^\%Error:', line)

            if errmatch:
                errors = errors + 1
            elif warnmatch:
                warnings = warnings +1

    chip.set('metric', step, index, 'errors', errors, clobber=True)
    chip.set('metric', step, index, 'warnings', warnings, clobber=True)

    #Return 0 if successful
    return 0

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("verilator.json")
