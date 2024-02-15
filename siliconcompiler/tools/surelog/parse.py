import os
import re
from siliconcompiler.tools._common import get_key_files, get_key_values, add_require_if_set
from siliconcompiler.tools.surelog.surelog import setup as setup_tool


##################################################
def setup(chip):
    '''
    Import verilog files
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'surelog'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    # Runtime parameters.
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Command-line options.
    options = []
    # -parse is slow but ensures the SV code is valid
    # we might want an option to control when to enable this
    # or replace surelog with a SV linter for the validate step
    options.append('-parse')
    # We don't use UHDM currently, so disable. For large designs, this file is
    # very big and takes a while to write out.
    options.append('-nouhdm')
    # Write back options to cfg
    chip.add('tool', tool, 'task', task, 'option', options, step=step, index=index)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    # Schema requirements
    add_require_if_set(chip, 'input', 'rtl', 'verilog')

    add_require_if_set(chip, 'option', 'ydir')
    add_require_if_set(chip, 'option', 'idir')
    add_require_if_set(chip, 'option', 'vlib')
    add_require_if_set(chip, 'option', 'cmdfile')


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

    cmdlist = []

    #####################
    # Library directories
    #####################

    for value in get_key_files(chip, 'option', 'ydir'):
        cmdlist.append('-y ' + value)

    #####################
    # Library files
    #####################

    for value in get_key_files(chip, 'option', 'vlib'):
        cmdlist.append('-v ' + value)

    #####################
    # Include paths
    #####################

    for value in get_key_files(chip, 'option', 'idir'):
        cmdlist.append('-I' + value)

    #######################
    # Variable Definitions
    #######################

    for value in get_key_values(chip, 'option', 'define'):
        cmdlist.append('-D' + value)

    #######################
    # Command files
    #######################

    for value in get_key_files(chip, 'option', 'cmdfile'):
        cmdlist.append('-f ' + value)

    #######################
    # Sources
    #######################

    for value in get_key_files(chip, 'input', 'rtl', 'verilog'):
        cmdlist.append(value)

    #######################
    # Top Module
    #######################

    cmdlist.append('-top ' + chip.top())

    ###############################
    # Parameters (top module only)
    ###############################

    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param in chip.getkeys('option', 'param'):
        value = chip.get('option', 'param', param)
        cmdlist.append(f'-P{param}={value}')

    return cmdlist


##################################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    # https://github.com/chipsalliance/Surelog/issues/3776#issuecomment-1652465581
    surelog_escape = re.compile(r"#~@([a-zA-Z_0-9.\$/\:\[\] ]*)#~@")

    # Look in slpp_all/file_elab.lst for list of Verilog files included in
    # design, read these and concatenate them into one pickled output file.
    with open('slpp_all/file_elab.lst', 'r') as filelist, \
            open(f'outputs/{chip.top()}.v', 'w') as outfile:
        for path in filelist.read().split('\n'):
            path = path.strip('"')
            if not path:
                # skip empty lines
                continue
            with open(path, 'r') as infile:
                infile_data = infile.read()
                unescaped_data = surelog_escape.sub(r"\\\1 ", infile_data)
                outfile.write(unescaped_data)
                if not unescaped_data.endswith('\n'):
                    # in case end of file is missing a newline
                    outfile.write('\n')
