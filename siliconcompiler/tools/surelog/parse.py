import os
import re

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
    chip.add('tool', tool, 'task', task, 'require', ",".join(['input', 'rtl', 'verilog']),
             step=step, index=index)

    libs = []
    libs.extend(chip.get('asic', 'logiclib', step=step, index=index))
    libs.extend(chip.get('asic', 'macrolib', step=step, index=index))

    def add_require_if_set(*key):
        if not chip.valid(*key):
            return
        if not chip.get(*key):
            return

        chip.add('tool', tool, 'task', task, 'require', ",".join(key),
                 step=step, index=index)

    opt_require = ['ydir', 'idir', 'vlib', 'cmdfile']
    for opt in opt_require:
        add_require_if_set('option', opt)
        for lib in libs:
            add_require_if_set('library', lib, 'option', opt)


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

    libs = []
    libs.extend(chip.get('asic', 'logiclib', step=step, index=index))
    libs.extend(chip.get('asic', 'macrolib', step=step, index=index))

    #####################
    # Library directories
    #####################

    ydir_files = chip.find_files('option', 'ydir')

    for item in libs:
        ydir_files.extend(chip.find_files('library', item, 'option', 'ydir'))

    # Deduplicated source files
    for value in _remove_dups(chip, 'ydir', ydir_files):
        cmdlist.append('-y ' + value)

    #####################
    # Library files
    #####################

    vlib_files = chip.find_files('option', 'vlib')

    for item in libs:
        vlib_files.extend(chip.find_files('library', item, 'option', 'vlib'))

    for value in _remove_dups(chip, 'vlib', vlib_files):
        cmdlist.append('-v ' + value)

    #####################
    # Include paths
    #####################

    idir_files = chip.find_files('option', 'idir')

    for item in libs:
        idir_files.extend(chip.find_files('library', item, 'option', 'idir'))

    for value in _remove_dups(chip, 'idir', idir_files):
        cmdlist.append('-I' + value)

    #######################
    # Variable Definitions
    #######################

    # Extra environment variable defines (don't need deduplicating)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D' + value)

    for item in libs:
        for value in chip.get('library', item, 'option', 'define'):
            cmdlist.append('-D' + value)

    #######################
    # Command files
    #######################

    # Command-line argument file(s).
    cmd_files = chip.find_files('option', 'cmdfile')

    for item in libs:
        cmd_files.extend(chip.find_files('library', item, 'option', 'cmdfile'))

    for value in _remove_dups(chip, 'cmdfile', cmd_files):
        cmdlist.append('-f ' + value)

    #######################
    # Sources
    #######################

    src_files = chip.find_files('input', 'rtl', 'verilog', step=step, index=index)

    # TODO: add back later
    # for item in libs:
    #    src_files.extend(chip.find_files('library', item, 'input', 'verilog'))

    for value in _remove_dups(chip, 'source', src_files):
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
