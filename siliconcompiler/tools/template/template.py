import os
import siliconcompiler

def make_docs():
    '''
    Tool description

    Documentation:https://
    Sources: https://
    Installation: https://

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','<step>')
    chip.set('arg','index','<index>')
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
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Required for all
    chip.set('eda', tool, 'exe', tool, clobber=False)
    chip.set('eda', tool, 'vswitch', '-version', clobber=False)
    chip.set('eda', tool, 'version', 'v2.0', clobber=False)
    chip.set('eda', tool, 'format', 'tcl', clobber=False)
    chip.set('eda', tool, 'option',  step, index, options, clobber=False)
    chip.set('eda', tool, 'threads', step, index, os.cpu_count(), clobber=False)

    # Required for script based tools
    chip.set('eda', tool, 'refdir',  step, index, refdir, clobber=False)
    chip.set('eda', tool, 'script',  step, index, refdir + script, clobber=False)
    for key in variables:
        chip.set('eda', tool, 'variable', step, index, key, variables[key], clobber=False)

    # Required for checker
    chip.add('eda', tool, 'output', step, index, outputs)
    chip.add('eda', tool, 'output', step, index, inputs)
    chip.add('eda', tool, 'require', step, index, requires)

def runtime_options(chip):
    '''
    Custom runtime options, returns list of command line options.
    '''

    cmdlist = []

    #resolve paths using chip.find_files

    return cmdlist

def parse_version(stdout):
    '''
    Version check based on stdout
    Depends on tool reported string
    '''
    #version = stdout.split()[1]
    #return version.split('+')[0]
    return 0

def pre_process(chip):
    '''
    Logic to run prior to executable
    '''
    return 0

def post_process(chip):
    '''
    Logic to run  executable
    '''

    # return 0 if successful

    return 0

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("template.json")
