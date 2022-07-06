import os
import shutil

import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step','import')
    chip.set('arg','index','0')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'bambu'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    refdir = 'tools/'+tool
    chip.set('tool', tool, 'exe', 'bambu')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.9.6', clobber=False)
    chip.set('tool', tool, 'refdir', step, index, refdir, clobber=False)
    chip.set('tool', tool, 'threads', step, index, os.cpu_count(), clobber=False)
    chip.set('tool', tool, 'option', step, index, [])

    # Input/Output requirements
    chip.add('tool', tool, 'output', step, index, chip.get_entrypoint() + '.v')

    # Schema requirements
    chip.add('tool', tool, 'require', step, index, 'input,c')

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
    for value in chip.find_files('input', 'c'):
        cmdlist.append(value)

    cmdlist.append('--top-fname=' + chip.get_entrypoint())

    return cmdlist

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    design = chip.get_entrypoint()
    shutil.copy(f'{design}.v', os.path.join('outputs', f'{design}.v'))
