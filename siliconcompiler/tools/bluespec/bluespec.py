
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

from siliconcompiler.tools.bluespec import convert
from siliconcompiler.tools._common import get_key_files, get_key_values


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    convert.setup(chip)
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

    bsc_path = ':'.join(get_key_files(chip, 'option', 'ydir') + ['%/Libraries'])
    cmdlist.append('-p ' + bsc_path)

    for value in get_key_files(chip, 'option', 'idir'):
        cmdlist.append('-I ' + value)
    for value in get_key_values(chip, 'option', 'define'):
        cmdlist.append('-D ' + value)

    sources = get_key_files(chip, 'input', 'hll', 'bsv')
    if len(sources) != 1:
        raise ValueError('Bluespec frontend only supports one source file!')
    cmdlist.append(sources[0])

    return cmdlist
