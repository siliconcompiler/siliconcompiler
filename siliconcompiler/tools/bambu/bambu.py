'''
'''

import importlib

####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    setup = getattr(importlib.import_module('tools.bambu.import'), 'setup')
    setup(chip)
    return chip

def parse_version(stdout):
    # Long multiline output, but second-to-last line looks like:
    # Version: PandA 0.9.6 - Revision 5e5e306b86383a7d85274d64977a3d71fdcff4fe-main
    version_line = stdout.split('\n')[-3]
    return version_line.split()[2]

################################
#  Custom runtime options
################################

def runtime_options(chip):

    cmdlist = []

    for value in chip.find_files('option', 'idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('input', 'hll', 'c'):
        cmdlist.append(value)

    cmdlist.append('--top-fname=' + chip.top())

    return cmdlist
