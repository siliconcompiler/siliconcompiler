import os
import re
from siliconcompiler.tools._common import \
    add_require_input, get_input_files, add_frontend_requires, get_frontend_options
from siliconcompiler.tools.surelog.surelog import setup as setup_tool
from siliconcompiler import sc_open


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
    add_require_input(chip, 'input', 'rtl', 'verilog')
    add_frontend_requires(chip, ['ydir', 'idir', 'vlib', 'cmdfile', 'libext', 'define', 'param'])


################################
#  Custom runtime options
################################
def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    opts = get_frontend_options(chip,
                                ['ydir',
                                 'idir',
                                 'vlib',
                                 'cmdfile',
                                 'libext',
                                 'define',
                                 'param'])

    cmdlist = []

    libext = opts['libext']
    if libext:
        libext_option = f"+libext+.{'+.'.join(libext)}"
    else:
        # default value for backwards compatibility
        libext_option = '+libext+.sv+.v'
    cmdlist.append(libext_option)

    #####################
    # Library directories
    #####################
    for value in opts['ydir']:
        cmdlist.append('-y ' + value)

    #####################
    # Library files
    #####################
    for value in opts['vlib']:
        cmdlist.append('-v ' + value)

    #####################
    # Include paths
    #####################
    for value in opts['idir']:
        cmdlist.append('-I' + value)

    #######################
    # Variable Definitions
    #######################
    for value in opts['define']:
        cmdlist.append('-D' + value)

    #######################
    # Command files
    #######################
    for value in opts['cmdfile']:
        cmdlist.append('-f ' + value)

    #######################
    # Sources
    #######################
    for value in get_input_files(chip, 'input', 'rtl', 'verilog'):
        cmdlist.append(value)

    #######################
    # Top Module
    #######################
    cmdlist.append('-top ' + chip.top())

    ###############################
    # Parameters (top module only)
    ###############################
    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param, value in opts['param']:
        cmdlist.append(f'-P{param}={value}')

    return cmdlist


##################################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    filemap = []
    with sc_open('slpp_all/file_map.lst') as filelist:
        for mapping in filelist:
            filemap.append(mapping)

    def lookup_sources(file):
        for fmap in filemap:
            if fmap.startswith(file):
                return fmap[len(file):].strip()
        return "unknown"

    # https://github.com/chipsalliance/Surelog/issues/3776#issuecomment-1652465581
    surelog_escape = re.compile(r"#~@([a-zA-Z_0-9.\$/\:\[\] ]*)#~@")

    # Look in slpp_all/file_elab.lst for list of Verilog files included in
    # design, read these and concatenate them into one pickled output file.
    with sc_open('slpp_all/file_elab.lst') as filelist, \
            open(f'outputs/{chip.top()}.v', 'w') as outfile:
        for path in filelist.read().split('\n'):
            path = path.strip('"')
            if not path:
                # skip empty lines
                continue
            with sc_open(path) as infile:
                source_files = lookup_sources(path)

                outfile.write(50*'/' + '\n')
                outfile.write(f'// Start of: {source_files}\n')

                infile_data = infile.read()
                unescaped_data = surelog_escape.sub(r"\\\1 ", infile_data)
                outfile.write(unescaped_data)
                if not unescaped_data.endswith('\n'):
                    # in case end of file is missing a newline
                    outfile.write('\n')

                outfile.write(f'// End of: {source_files}\n')
                outfile.write(50*'/' + '\n')
