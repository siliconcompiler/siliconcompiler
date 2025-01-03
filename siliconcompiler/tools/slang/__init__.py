'''
slang is a software library that provides various components for lexing, parsing, type checking,
and elaborating SystemVerilog code. It comes with an executable tool that can compile and lint
any SystemVerilog project, but it is also intended to be usable as a front end for synthesis
tools, simulators, linters, code editors, and refactoring tools.

Documentation: https://sv-lang.com/

Sources: https://github.com/MikePopoloski/slang

Installation: https://sv-lang.com/building.html
'''
import pyslang
from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_frontend_options, get_input_files, get_tool_task


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    add_require_input(chip, 'input', 'rtl', 'verilog')
    add_require_input(chip, 'input', 'rtl', 'systemverilog')
    add_require_input(chip, 'input', 'cmdfile', 'f')
    add_frontend_requires(chip, ['ydir', 'idir', 'vlib', 'libext', 'define', 'param'])


def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    options = chip.get('tool', tool, 'task', task, 'option', step=step, index=index)

    options.extend(['--threads', str(chip.get('tool', tool, 'task', task, 'threads',
                                              step=step, index=index))])

    opts = get_frontend_options(chip,
                                ['ydir',
                                 'idir',
                                 'vlib',
                                 'libext',
                                 'define',
                                 'param'])

    if opts['libext']:
        options.extend(['--libext', f'{",".join(opts["libext"])}'])

    #####################
    # Library directories
    #####################
    if opts['ydir']:
        options.extend(['-y', f'{",".join(opts["ydir"])}'])

    #####################
    # Library files
    #####################
    if opts['vlib']:
        options.extend(['-libfile', f'{",".join(opts["vlib"])}'])

    #####################
    # Include paths
    #####################
    if opts['idir']:
        options.extend(['--include-directory', f'{",".join(opts["idir"])}'])

    #######################
    # Variable Definitions
    #######################
    for value in opts['define']:
        options.extend(['-D', value])

    #######################
    # Command files
    #######################
    cmdfiles = get_input_files(chip, 'input', 'cmdfile', 'f')
    if cmdfiles:
        options.extend(['-F', f'{",".join(cmdfiles)}'])

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
    # if chip.get('option', 'frontend') == 'verilog' or \
    #    chip.get('option', 'frontend') == 'systemverilog':
    options.extend(['--top', chip.top()])

    ###############################
    # Parameters (top module only)
    ###############################
    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param, value in opts['param']:
        options.extend(['-G', f'{param}={value}'])

    options.append('--single-unit')

    return options


def _get_driver(chip, options_func):
    driver = pyslang.Driver()
    driver.addStandardArgs()

    options = options_func(chip)

    parseOpts = pyslang.CommandLineOptions()
    parseOpts.ignoreProgramName = True
    opts = " ".join(options)
    if not driver.parseCommandLine(opts, parseOpts):
        return driver, 1

    if not driver.processOptions():
        return driver, 2

    return driver, 0


def _compile(chip, driver):
    ok = driver.parseAllSources()
    compilation = driver.createCompilation()
    ok = ok & driver.reportCompilation(compilation, False)

    return compilation, ok
