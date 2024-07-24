'''
Lint system verilog
'''
from siliconcompiler.tools import slang
from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_frontend_options, get_input_files, get_tool_task
import os


def setup(chip):
    slang.setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             clobber=False, step=step, index=index)

    add_require_input(chip, 'input', 'rtl', 'verilog')
    add_require_input(chip, 'input', 'rtl', 'systemverilog')
    add_frontend_requires(chip, ['ydir', 'idir', 'vlib', 'libext', 'define', 'param'])


def runtime_options(chip):
    options = ["-lint-only"]

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
        options.append(f'-G {param}={value}')

    return options


def post_process(chip):
    slang.post_process(chip)
