import os
import shutil

import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    Bluespec is a high-level hardware description language. It has a variety of
    advanced features including a powerful type system that can prevent errors
    prior to synthesis time, and its most distinguishing feature, Guarded Atomic
    Actions, allow you to define hardware components in a modular manner based
    on their invariants, and let the compiler pick a scheduler.

    Documentation: https://github.com/B-Lang-org/bsc#documentation

    Sources: https://github.com/B-Lang-org/bsc

    Installation: https://github.com/B-Lang-org/bsc#download
    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step','import')
    chip.set('arg','index','0')
    setup(chip)
    return chip

# Directory inside step/index dir to store bsc intermediate results.
VLOG_DIR = 'verilog'

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'bluespec'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    refdir = 'tools/'+tool
    chip.set('tool', tool, 'exe', 'bsc')
    # This is technically the 'verbose' flag, but used alone it happens to give
    # us the version and exit cleanly, so we'll use it here.
    chip.set('tool', tool, 'vswitch', '-v')
    chip.set('tool', tool, 'version', '>=2021.07', clobber=False)
    chip.set('tool', tool, 'refdir', step, index,  refdir, clobber=False)
    chip.set('tool', tool, 'threads', step, index,  os.cpu_count(), clobber=False)
    chip.set('tool', tool, 'option', step, index,  [], clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'output', step, index, chip.top() + '.v')

    # Schema requirements
    chip.add('tool', tool, 'require', step, index, 'input,bsv')

def parse_version(stdout):
    # Examples:
    # Bluespec Compiler, version 2021.12.1-27-g9a7d5e05 (build 9a7d5e05)
    # Bluespec Compiler, version 2021.07 (build 4cac6eba)

    long_version = stdout.split()[3]
    return long_version.split('-')[0]

################################
#  Custom runtime options
################################

def runtime_options(chip):
    cmdlist = []

    design = chip.top()

    cmdlist.append('-verilog')
    cmdlist.append(f'-vdir {VLOG_DIR}')
    cmdlist.append('-u')
    cmdlist.append(f'-g {design}')

    bsc_path = ':'.join(chip.find_files('option', 'ydir') + ['%/Libraries'])
    cmdlist.append('-p ' + bsc_path)

    for value in chip.find_files('option', 'idir'):
        cmdlist.append('-I ' + value)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D ' + value)

    sources = chip.find_files('input', 'bsv')
    if len(sources) != 1:
        raise ValueError('Bluespec frontend only supports one source file!')
    cmdlist.append(sources[0])

    return cmdlist

################################
# Pre-process
################################

def pre_process(chip):
    # bsc requires its output directory exists before being called.
    if os.path.isdir(VLOG_DIR):
        shutil.rmtree(VLOG_DIR)
    os.makedirs(VLOG_DIR)

################################
# Post-process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    # bsc outputs each compiled module to its own Verilog file, so we
    # concatenate them all to create a pickled output we can pass along.
    design = chip.top()
    with open(os.path.join('outputs', f'{design}.v'), 'w') as pickled_vlog:
        for src in os.listdir(VLOG_DIR):
            with open(os.path.join(VLOG_DIR, src), 'r') as vlog_mod:
                pickled_vlog.write(vlog_mod.read())
