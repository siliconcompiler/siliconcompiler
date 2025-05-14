import os
import re
from siliconcompiler.tools._common import \
    add_require_input, get_input_files, add_frontend_requires, get_frontend_options, \
    get_tool_task, has_input_files
from siliconcompiler.tools.surelog import setup as setup_tool
from siliconcompiler.tools.surelog import runtime_options as runtime_options_tool
from siliconcompiler import sc_open
from siliconcompiler import utils


##################################################
def setup(chip):
    '''
    Import verilog files
    '''

    if not has_input_files(chip, 'input', 'rtl', 'verilog') and \
       not has_input_files(chip, 'input', 'rtl', 'systemverilog'):
        return "no files in [input,rtl,systemverilog] or [input,rtl,verilog]"

    # Generic tool setup.
    setup_tool(chip)

    tool = 'surelog'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Runtime parameters.
    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index, clobber=False)

    # Input/Output requirements
    chip.set('tool', tool, 'task', task, 'output', __outputfile(chip), step=step, index=index)

    # Schema requirements
    add_require_input(chip, 'input', 'rtl', 'verilog')
    add_require_input(chip, 'input', 'rtl', 'systemverilog')
    add_require_input(chip, 'input', 'cmdfile', 'f')
    add_frontend_requires(chip, ['ydir', 'idir', 'vlib', 'libext', 'define', 'param'])


################################
#  Custom runtime options
################################
def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    opts = get_frontend_options(chip,
                                ['ydir',
                                 'idir',
                                 'vlib',
                                 'libext',
                                 'define',
                                 'param'])

    # Command-line options.
    cmdlist = runtime_options_tool(chip)

    # -parse is slow but ensures the SV code is valid
    # we might want an option to control when to enable this
    # or replace surelog with a SV linter for the validate step
    cmdlist.append('-parse')
    # We don't use UHDM currently, so disable. For large designs, this file is
    # very big and takes a while to write out.
    cmdlist.append('-nouhdm')

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
        cmdlist.extend(['-y', value])

    #####################
    # Library files
    #####################
    for value in opts['vlib']:
        cmdlist.extend(['-v', value])

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
    for value in get_input_files(chip, 'input', 'cmdfile', 'f'):
        cmdlist.extend(['-f', + value])

    #######################
    # Sources
    #######################
    for value in get_input_files(chip, 'input', 'rtl', 'systemverilog'):
        cmdlist.append(value)
    for value in get_input_files(chip, 'input', 'rtl', 'verilog'):
        cmdlist.append(value)

    #######################
    # Top Module
    #######################
    cmdlist.extend(['-top', chip.top(step, index)])

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
    output_template = utils.get_file_template('output.v',
                                              root=os.path.join(os.path.dirname(__file__),
                                                                'templates'))

    with sc_open('slpp_all/file_elab.lst') as filelist, \
            open(f'outputs/{__outputfile(chip)}', 'w') as outfile:
        for path in filelist.read().split('\n'):
            path = path.strip('"')
            if not path:
                # skip empty lines
                continue
            with sc_open(path) as infile:
                source_files = lookup_sources(path)
                unescaped_data = surelog_escape.sub(r"\\\1 ", infile.read())

                outfile.write(output_template.render(
                    source_file=source_files,
                    content=unescaped_data
                ))

                outfile.write('\n')


def __outputfile(chip):
    is_systemverilog = has_input_files(chip, 'input', 'rtl', 'systemverilog')
    if is_systemverilog:
        return f'{chip.top()}.sv'
    return f'{chip.top()}.v'
