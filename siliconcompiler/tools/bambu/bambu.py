import os
import shutil

import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','import')
    chip.set('arg','index','0')
    chip.set('design', '<design>')
    setup_tool(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'bambu'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    refdir = 'tools/'+tool
    chip.set('eda', tool, 'exe', 'bambu', clobber=False)
    chip.set('eda', tool, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, 'version', '0.9.6', clobber=False)
    chip.set('eda', tool, 'refdir', step, index, refdir, clobber=False)
    chip.set('eda', tool, 'threads', step, index, os.cpu_count(), clobber=False)
    chip.set('eda', tool, 'option', step, index, [])

    # Input/Output requirements
    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.v')

def parse_version(stdout):
    # Long multiline output, but second-to-last line looks like:
    # Version: PandA 0.9.6 - Revision 5e5e306b86383a7d85274d64977a3d71fdcff4fe-main
    version_line = stdout.split('\n')[-2]
    return version_line.split()[2]

################################
#  Custom runtime options
################################

def runtime_options(chip):

    cmdlist = []

    for value in chip.find_files('idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('source'):
        cmdlist.append(value)

    cmdlist.append('--top-fname=' + chip.get('design'))

    return cmdlist

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    design = chip.get('design')
    shutil.copy(f'{design}.v', os.path.join('outputs', f'{design}.v'))

    return 0
