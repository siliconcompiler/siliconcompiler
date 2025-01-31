'''
slang is a software library that provides various components for lexing, parsing, type checking,
and elaborating SystemVerilog code. It comes with an executable tool that can compile and lint
any SystemVerilog project, but it is also intended to be usable as a front end for synthesis
tools, simulators, linters, code editors, and refactoring tools.

Documentation: https://sv-lang.com/

Sources: https://github.com/MikePopoloski/slang

Installation: https://sv-lang.com/building.html
'''
import re
from siliconcompiler import sc_open
from siliconcompiler.tools._common import record_metric
from siliconcompiler.tools._common import \
    get_frontend_options, get_input_files, get_tool_task


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    tool = 'slang'

    # Standard Setup
    chip.set('tool', tool, 'exe', 'slang')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=6.0', clobber=False)


def parse_version(stdout):
    # slang --version output looks like:
    # slang version 6.0.121+c2c478cf

    # grab version # by splitting on whitespace
    return stdout.strip().split()[-1].split('+')[0]


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    log = f'{step}.log'
    with sc_open(log) as f:
        for line in f:
            match = re.search(r'(\d+) errors, (\d+) warnings', line)
            if match:
                record_metric(chip, step, index, 'errors', match.group(1), log)
                record_metric(chip, step, index, 'warnings', match.group(2), log)


def common_runtime_options(chip):
    options = []

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    options.extend(['-j', str(chip.get('tool', tool, 'task', task, 'threads',
                              step=step, index=index))])

    opts = get_frontend_options(chip,
                                ['ydir',
                                 'idir',
                                 'vlib',
                                 'libext',
                                 'define',
                                 'param'])

    if opts['libext']:
        options.append(f'--libext {",".join(opts["libext"])}')

    #####################
    # Library directories
    #####################
    if opts['ydir']:
        options.append(f'-y {",".join(opts["ydir"])}')

    #####################
    # Library files
    #####################
    if opts['vlib']:
        options.append(f'-libfile {",".join(opts["vlib"])}')

    #####################
    # Include paths
    #####################
    if opts['idir']:
        options.append(f'--include-directory {",".join(opts["idir"])}')

    #######################
    # Variable Definitions
    #######################
    for value in opts['define']:
        options.append('-D ' + value)

    #######################
    # Command files
    #######################
    cmdfiles = get_input_files(chip, 'input', 'cmdfile', 'f')
    if cmdfiles:
        options.append(f'-F {",".join(cmdfiles)}')

    #######################
    # Sources
    #######################
    for value in get_input_files(chip, 'input', 'rtl', 'systemverilog'):
        options.append(value)
    for value in get_input_files(chip, 'input', 'rtl', 'verilog'):
        options.append(value)

    #######################
    # Top Module
    #######################
    options.append('--top ' + chip.top())

    ###############################
    # Parameters (top module only)
    ###############################
    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param, value in opts['param']:
        value = value.replace('"', '\\"')
        options.append(f'-G {param}={value}')

    return options
