'''
Surelog is a SystemVerilog pre-processor, parser, elaborator,
and UHDM compiler that provdes IEEE design and testbench
C/C++ VPI and a Python AST API.

Documentation: https://github.com/chipsalliance/Surelog

Sources: https://github.com/chipsalliance/Surelog

Installation: https://github.com/chipsalliance/Surelog
'''

import os
import sys
import shutil


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    ''' Sets up default settings common to running Surelog.
    '''

    tool = 'surelog'
    # Nothing in this method should rely on the value of 'step' or 'index', but they are used
    # as schema keys in some important places, so we still need to fetch them.
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    exe = tool
    task = chip._get_task(step, index)

    # Although Windows will find the binary even if the .exe suffix is omitted,
    # Surelog won't find the relative builtin.sv file unless we add it.
    if sys.platform.startswith('win32'):
        exe = f'{tool}.exe'

    # Standard Setup
    chip.set('tool', tool, 'exe', exe)
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=1.51', clobber=False)

    # Command-line options.
    options = []

    # With newer versions of Surelog (at least 1.35 and up), this option is
    # necessary to make bundled versions work.
    # TODO: why?
    options.append('-nocache')

    # Wite back options to cfg
    chip.add('tool', tool, 'task', task, 'option', options, step=step, index=index)

    # We package SC wheels with a precompiled copy of Surelog installed to
    # tools/surelog/bin. If the user doesn't have Surelog installed on their
    # system path, set the path to the bundled copy in the schema.
    if shutil.which(exe) is None:
        surelog_path = os.path.join(os.path.dirname(__file__), 'bin')
        if os.path.exists(os.path.join(surelog_path, exe)):
            chip.set('tool', tool, 'path', surelog_path, clobber=False)

    # Log file parsing
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^\[WRN:',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^\[(ERR|FTL|SNT):',
             step=step, index=index, clobber=False)

    for warning in chip.get('tool', tool, 'task', task, 'warningoff', step=step, index=index):
        chip.add('tool', tool, 'regex', step, index, 'warnings', f'-v {warning}',
                 step=step, index=index)


def parse_version(stdout):
    # Surelog --version output looks like:
    # VERSION: 1.13
    # BUILT  : Nov 10 2021

    # grab version # by splitting on whitespace
    return stdout.split()[1]


################################
#  Custom runtime options
################################
def _remove_dups(chip, type, file_set):
    new_files = []
    for f in file_set:
        if f not in new_files:
            new_files.append(f)
        else:
            chip.logger.warning(f"Removing duplicate '{type}' inputs: {f}")
    return new_files


def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    cmdlist = []

    #####################
    # Library directories
    #####################

    ydir_files = chip.find_files('option', 'ydir')

    for item in chip.getkeys('library'):
        ydir_files.extend(chip.find_files('library', item, 'option', 'ydir'))

    # Deduplicated source files
    for value in _remove_dups(chip, 'ydir', ydir_files):
        cmdlist.append('-y ' + value)

    #####################
    # Library files
    #####################

    vlib_files = chip.find_files('option', 'vlib')

    for item in chip.getkeys('library'):
        vlib_files.extend(chip.find_files('library', item, 'option', 'vlib'))

    for value in _remove_dups(chip, 'vlib', vlib_files):
        cmdlist.append('-v ' + value)

    #####################
    # Include paths
    #####################

    idir_files = chip.find_files('option', 'idir')

    for item in chip.getkeys('library'):
        idir_files.extend(chip.find_files('library', item, 'option', 'idir'))

    for value in _remove_dups(chip, 'idir', idir_files):
        cmdlist.append('-I' + value)

    #######################
    # Variable Definitions
    #######################

    # Extra environment variable defines (don't need deduplicating)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D' + value)

    for item in chip.getkeys('library'):
        for value in chip.get('library', item, 'option', 'define'):
            cmdlist.append('-D' + value)

    #######################
    # Command files
    #######################

    # Command-line argument file(s).
    cmd_files = chip.find_files('option', 'cmdfile')

    for item in chip.getkeys('library'):
        cmd_files.extend(chip.find_files('library', item, 'option', 'cmdfile'))

    for value in _remove_dups(chip, 'cmdfile', cmd_files):
        cmdlist.append('-f ' + value)

    #######################
    # Sources
    #######################

    src_files = chip.find_files('input', 'rtl', 'verilog', step=step, index=index)

    # TODO: add back later
    # for item in chip.getkeys('library'):
    #    src_files.extend(chip.find_files('library', item, 'input', 'verilog'))

    for value in _remove_dups(chip, 'source', src_files):
        cmdlist.append(value)

    #######################
    # Top Module
    #######################

    cmdlist.append('-top ' + chip.top())

    #######################
    # Lib extensions
    #######################

    # make sure we can find .sv files in ydirs
    # TODO: need to add libext
    cmdlist.append('+libext+.sv+.v')

    ###############################
    # Parameters (top module only)
    ###############################

    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param in chip.getkeys('option', 'param'):
        value = chip.get('option', 'param', param)
        cmdlist.append(f'-P{param}={value}')

    return cmdlist
