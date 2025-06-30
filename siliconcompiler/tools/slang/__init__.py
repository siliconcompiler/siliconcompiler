'''
slang is a software library that provides various components for lexing, parsing, type checking,
and elaborating SystemVerilog code. It comes with an executable tool that can compile and lint
any SystemVerilog project, but it is also intended to be usable as a front end for synthesis
tools, simulators, linters, code editors, and refactoring tools.

Documentation: https://sv-lang.com/

Sources: https://github.com/MikePopoloski/slang

Installation: https://sv-lang.com/building.html
'''
import os
import shlex

try:
    import pyslang
except ModuleNotFoundError:
    pyslang = None

from siliconcompiler import utils
from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_frontend_options, get_input_files, \
    get_tool_task, record_metric


from siliconcompiler.tool import FrontendTask


class SlangTask(FrontendTask):
    def __init__(self):
        super().__init__()

        check_version = test_version()
        if check_version:
            raise RuntimeError(check_version)

    def tool(self):
        return "slang"

    def setup(self):
        self.set("threads", utils.get_cores(None), clobber=False)
        return super().setup()

    def runtime_options(self):
        options = super().runtime_options()

        options.append('--single-unit')

        options.extend(['--threads', self.get("threads")])

        # opts = get_frontend_options(chip,
        #                             ['ydir',
        #                             'idir',
        #                             'vlib',
        #                             'libext',
        #                             'define',
        #                             'param'])

        # if opts['libext']:
        #     options.extend(['--libext', f'{",".join(opts["libext"])}'])

        # #####################
        # # Library directories
        # #####################
        # if opts['ydir']:
        #     options.extend(['-y', f'{",".join(opts["ydir"])}'])

        # #####################
        # # Library files
        # #####################
        # if opts['vlib']:
        #     options.extend(['-libfile', f'{",".join(opts["vlib"])}'])

        # #####################
        # # Include paths
        # #####################
        # if opts['idir']:
        #     options.extend(['--include-directory', f'{",".join(opts["idir"])}'])

        # #######################
        # # Variable Definitions
        # #######################
        # for value in opts['define']:
        #     options.extend(['-D', value])

        # #######################
        # # Command files
        # #######################
        # cmdfiles = get_input_files(chip, 'input', 'cmdfile', 'f')
        # if cmdfiles:
        #     options.extend(['-F', f'{",".join(cmdfiles)}'])

        #######################
        # Sources
        #######################
        fileset = "rtl"
        for value in self.get_files(fileset, "systemverilog"):
            options.append(value)
        for value in self.get_files(fileset, "verilog"):
            options.append(value)

        #######################
        # Top Module
        #######################
        options.extend(['--top', self.design_topmodule()])

        ###############################
        # Parameters (top module only)
        ###############################
        # Set up user-provided parameters to ensure we elaborate the correct modules
        # for param, value in opts['param']:
        #     options.extend(['-G', f'{param}={value}'])

        return options

    def _init_driver(self, ignored_diagnotics=None):
        self._driver = pyslang.Driver()
        self._driver.addStandardArgs()

        parse_options = pyslang.CommandLineOptions()
        parse_options.ignoreProgramName = True
        opts = shlex.join(self.get_runtime_arguments())
        self.logger().info(f"runtime arguments: {opts}")
        self._error_code = 0
        if not self._driver.parseCommandLine(opts, parse_options):
            self._error_code = 1

        if self._error_code == 0 and not self._driver.processOptions():
            self._error_code = 2

        for warning in self.get('warningoff'):
            if hasattr(pyslang.Diags, warning):
                self._driver.diagEngine.setSeverity(
                    getattr(pyslang.Diags, warning),
                    pyslang.DiagnosticSeverity.Ignored)
            else:
                self.logger().warning(f'{warning} is not a valid slang category')

        if not ignored_diagnotics:
            ignored_diagnotics = []
        for ignore in ignored_diagnotics:
            self._driver.diagEngine.setSeverity(
                ignore,
                pyslang.DiagnosticSeverity.Ignored)

    def _compile(self):
        ok = self._driver.parseAllSources()
        self._compilation = self._driver.createCompilation()

        return ok

    def _diagnostics(self):
        report = {
            "error": [],
            "warning": [],
        }
        diags = self._driver.diagEngine
        for diag in self._compilation.getAllDiagnostics():
            severity = diags.getSeverity(diag.code, diag.location)
            report_level = None
            if severity == pyslang.DiagnosticSeverity.Warning:
                report_level = "warning"
            elif severity == pyslang.DiagnosticSeverity.Error:
                report_level = "error"
            elif severity == pyslang.DiagnosticSeverity.Fatal:
                report_level = "error"

            if report_level:
                for n, line in enumerate(
                        diags.reportAll(self._driver.sourceManager, [diag]).splitlines()):
                    if line.strip():
                        if n == 0:
                            line_parts = line.split(":")
                            if os.path.exists(line_parts[0]):
                                line_parts[0] = os.path.abspath(line_parts[0])
                            line = ":".join(line_parts)

                        report[report_level].append(line)

        if report["warning"]:
            for line in report["warning"]:
                self.logger().warning(line)
        if report["error"]:
            for line in report["error"]:
                self.logger().error(line)

        diags.clearCounts()
        for diag in self._compilation.getAllDiagnostics():
            diags.issue(diag)

        self.schema("metric").record(*self.node(), "errors", diags.numErrors)
        self.add("report", "errors", f'sc_{self.node()[0]}_{self.node()[1]}.log')
        self.schema("metric").record(*self.node(), "warnings", diags.numWarnings)
        self.add("report", "warnings", f'sc_{self.node()[0]}_{self.node()[1]}.log')


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
    options.extend(['--top', chip.top()])

    ###############################
    # Parameters (top module only)
    ###############################
    # Set up user-provided parameters to ensure we elaborate the correct modules
    # for param, value in opts['param']:
    #     options.extend(['-G', f'{param}={value}'])

    return options


def _get_driver(chip, options_func, ignored_diagnotics=None):
    driver = pyslang.Driver()
    driver.addStandardArgs()

    options = options_func(chip)

    parse_options = pyslang.CommandLineOptions()
    parse_options.ignoreProgramName = True
    opts = shlex.join(options)
    chip.logger.info(f"runtime arguments: {opts}")
    code = 0
    if not driver.parseCommandLine(opts, parse_options):
        code = 1

    if code == 0 and not driver.processOptions():
        code = 2

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    for warning in chip.get('tool', tool, 'task', task, 'warningoff', step=step, index=index):
        if hasattr(pyslang.Diags, warning):
            driver.diagEngine.setSeverity(
                getattr(pyslang.Diags, warning),
                pyslang.DiagnosticSeverity.Ignored)
        else:
            chip.logger.warning(f'{warning} is not a valid slang category')

    if not ignored_diagnotics:
        ignored_diagnotics = []
    for ignore in ignored_diagnotics:
        driver.diagEngine.setSeverity(
            ignore,
            pyslang.DiagnosticSeverity.Ignored)

    return driver, code


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
            for n, line in enumerate(diags.reportAll(driver.sourceManager, [diag]).splitlines()):
                if line.strip():
                    if n == 0:
                        line_parts = line.split(":")
                        if os.path.exists(line_parts[0]):
                            line_parts[0] = os.path.abspath(line_parts[0])
                        line = ":".join(line_parts)

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

    record_metric(chip, step, index, 'errors', diags.numErrors, [f'sc_{step}_{index}.log'])
    record_metric(chip, step, index, 'warnings', diags.numWarnings, [f'sc_{step}_{index}.log'])
