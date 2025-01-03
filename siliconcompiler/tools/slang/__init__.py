'''
slang is a software library that provides various components for lexing, parsing, type checking,
and elaborating SystemVerilog code. It comes with an executable tool that can compile and lint
any SystemVerilog project, but it is also intended to be usable as a front end for synthesis
tools, simulators, linters, code editors, and refactoring tools.

Documentation: https://sv-lang.com/

Sources: https://github.com/MikePopoloski/slang

Installation: https://sv-lang.com/building.html
'''
try:
    import pyslang
except ModuleNotFoundError:
    pyslang = None

from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_frontend_options, get_input_files, \
    get_tool_task, record_metric


def has_pyslang():
    return pyslang is not None


def test_version():
    if not has_pyslang():
        return "pyslang is not installed"

    version = pyslang.VersionInfo
    if version.getMajor() >= 7 and version.getMinor() >= 0:
        return None

    ver = f"{version.getMajor()}.{version.getMinor()}.{version.getPatch()}"

    return f"incorrect pyslang version: {ver}"


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    add_require_input(chip, 'input', 'rtl', 'verilog')
    add_require_input(chip, 'input', 'rtl', 'systemverilog')
    add_require_input(chip, 'input', 'cmdfile', 'f')
    add_frontend_requires(chip, ['ydir', 'idir', 'vlib', 'libext', 'define', 'param'])


def common_runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    options = chip.get('tool', tool, 'task', task, 'option', step=step, index=index)

    options.append('--single-unit')

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
    options.append('--top ' + chip.top(step, index))

    ###############################
    # Parameters (top module only)
    ###############################
    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param, value in opts['param']:
        value = value.replace('"', '\\"')
        options.append(f'-G {param}={value}')

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
    return compilation, ok


def _diagnostics(chip, driver, compilation):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    report = {
        "error": [],
        "warning": [],
    }
    diags = driver.diagEngine
    for diag in compilation.getAllDiagnostics():
        severity = diags.getSeverity(diag.code, diag.location)
        report_level = None
        if severity == pyslang.DiagnosticSeverity.Warning:
            report_level = "warning"
        elif severity == pyslang.DiagnosticSeverity.Error:
            report_level = "error"
        elif severity == pyslang.DiagnosticSeverity.Fatal:
            report_level = "error"

        if report_level:
            for line in diags.reportAll(driver.sourceManager, [diag]).splitlines():
                if line.strip():
                    report[report_level].append(line)

    if report["warning"]:
        for line in report["warning"]:
            chip.logger.warning(line)
    if report["error"]:
        for line in report["error"]:
            chip.logger.error(line)

    diags.clearCounts()
    for diag in compilation.getAllDiagnostics():
        diags.issue(diag)

    record_metric(chip, step, index, 'errors', diags.numErrors, [])
    record_metric(chip, step, index, 'warnings', diags.numWarnings, [])
