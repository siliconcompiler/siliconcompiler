'''
Verilator is a free and open-source software tool which converts Verilog (a
hardware description language) to a cycle-accurate behavioral model in C++
or SystemC.

For all steps, this driver runs Verilator using the ``-sv`` switch to enable
parsing a subset of SystemVerilog features. All steps also support using
:keypath:`option, relax` to make warnings nonfatal.

Documentation: https://verilator.org/guide/latest

Sources: https://github.com/verilator/verilator

Installation: https://verilator.org/guide/latest/install.html
'''

import os


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    chip.load_target("freepdk45_demo")


def setup(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings. Static setings only.
    '''

    tool = 'verilator'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    # Basic Tool Setup
    chip.set('tool', tool, 'exe', 'verilator')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=4.028', clobber=False)

    # Common to all tasks
    # Max threads
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(), step=step, index=index, clobber=False)

    # Basic warning and error grep check on logfile
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r"^\%Warning", step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r"^\%Error", step=step, index=index, clobber=False)

    # Generic CLI options (for all steps)
    chip.set('tool', tool, 'task', task, 'option', '-sv', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'option', f'--top-module {design}', step=step, index=index)

    # Make warnings non-fatal in relaxed mode
    if chip.get('option', 'relax'):
        chip.add('tool', tool, 'task', task, 'option', ['-Wno-fatal', '-Wno-UNOPTFLAT'], step=step, index=index)

    # Converting user setting to verilator specific filter
    # for warning in chip.get('tool', tool, 'task', task, step, index, 'warningoff'):
    #    chip.add('tool', tool, 'task', task, 'option', f'-Wno-{warning}', step=step, index=index)

    # User runtime option
    if chip.get('option', 'trace', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'task', task, 'option', '--trace', step=step, index=index)

################################
#  Custom runtime options
################################


def runtime_options(chip):
    '''
    CLI options that involve filepaths (must be resolved at runtime, in case
    we're running on a different machine than client).
    '''
    cmdlist = []
    tool = 'verilator'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    if task == 'parse':
        for value in chip.find_files('option', 'ydir'):
            cmdlist.append('-y ' + value)
        for value in chip.find_files('option', 'vlib'):
            cmdlist.append('-v ' + value)
        for value in chip.find_files('option', 'idir'):
            cmdlist.append('-I' + value)
        for value in chip.find_files('option', 'cmdfile'):
            cmdlist.append('-f ' + value)
        for value in chip.find_files('input', 'rtl', 'verilog', step=step, index=index):
            cmdlist.append(value)
    elif task == 'compile':
        for value in chip.find_files('input', 'hll', 'c', step=step, index=index):
            cmdlist.append(value)
        for value in chip.find_files('tool', tool, 'task', task, 'input', step=step, index=index):
            cmdlist.append(value)

    return cmdlist

################################
# Version Check
################################


def parse_version(stdout):
    # Verilator 4.104 2020-11-14 rev v4.104
    return stdout.split()[1]


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("verilator.csv")
