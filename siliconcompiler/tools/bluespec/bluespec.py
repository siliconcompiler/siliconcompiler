import importlib
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
    step = 'import'
    index = '0'
    flow = '<flow>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('option', 'flow', flow)
    chip.set('flowgraph', flow, step, index, 'task', '<task>')
    setup = getattr(importlib.import_module('tools.bluespec.import'), 'setup')
    setup(chip)
    return chip

# Directory inside step/index dir to store bsc intermediate results.
VLOG_DIR = 'verilog'

################################
# Setup Tool (pre executable)
################################

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

    sources = chip.find_files('input', 'hll', 'bsv')
    if len(sources) != 1:
        raise ValueError('Bluespec frontend only supports one source file!')
    cmdlist.append(sources[0])

    return cmdlist
