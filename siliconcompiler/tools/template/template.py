'''
Tool description

Documentation: https://

Sources: https://

Installation: https://
'''

import os
import siliconcompiler
from siliconcompiler.tools._common import get_tool_task


def make_docs():

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg', 'step', '<step>')
    chip.set('arg', 'index', '<index>')
    setup(chip)
    return chip


def setup(chip):
    '''
    Setup Tool (pre executable)
    '''

    ##################################
    # Simple settings
    ##################################

    tool = 'template'                    # tool name, must match file name
    exe = ''                             # name of executable
    refdir = ''                          # path to reference scripts
    script = ''                          # path to entry script
    options = ''                         # executable command line options
    outputs = []                         # output files (inside ./outputs)
    inputs = []                          # input files (inside ./inputs)
    requires = []                        # required parameters
    variables = {}                       # key/value tool variables

    ##################################
    # Advanced settings below
    ##################################

    # Fetching current step and index
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Required for all
    chip.set('tool', tool, 'exe', exe)
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'version', 'v2.0', clobber=False)

    # Required for script tools
    chip.set('tool', tool, 'format', 'tcl', clobber=False)

    chip.set('tool', tool, 'task', task, 'option', options,
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Required for script based tools
    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'script', refdir + script,
             step=step, index=index, clobber=False)
    for key in variables:
        chip.set('tool', tool, 'task', task, 'var', key, variables[key],
                 step=step, index=index, clobber=False)

    # Required for checker
    chip.add('tool', tool, 'task', task, 'output', outputs,
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'input', inputs,
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', requires,
             step=step, index=index)


def runtime_options(chip):
    '''
    Custom runtime options, returns list of command line options.
    '''

    cmdlist = []

    # resolve paths using chip.find_files

    return cmdlist


def parse_version(stdout):
    '''
    Version check based on stdout
    Depends on tool reported string
    '''
    # version = stdout.split()[1]
    # return version.split('+')[0]
    return 0


def pre_process(chip):
    '''
    Logic to run prior to executable
    '''
    pass


def post_process(chip):
    '''
    Logic to run after executable
    '''
    pass


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("template.json")
