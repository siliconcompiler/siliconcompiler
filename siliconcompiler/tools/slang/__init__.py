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

from siliconcompiler import Task


class SlangTask(Task):
    def __init__(self):
        super().__init__()

        check_version = self.__test_version()
        if check_version:
            raise RuntimeError(check_version)

    def __test_version(self):
        if pyslang is None:
            return "pyslang is not installed"

        version = pyslang.VersionInfo
        if version.getMajor() >= 9 and version.getMinor() >= 0:
            return None

        ver = f"{version.getMajor()}.{version.getMinor()}.{version.getPatch()}"

        return f"incorrect pyslang version: {ver}"

    def tool(self):
        return "slang"

    def setup(self):
        super().setup()

        self.set_threads()

        self.set_logdestination("stdout", "log")
        self.set_logdestination("stderr", "log")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.has_idir(fileset):
                self.add_required_key(lib, "fileset", fileset, "idir")
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.get("fileset", fileset, "undefine"):
                self.add_required_key(lib, "fileset", fileset, "undefine")
            if lib.has_file(fileset=fileset, filetype="commandfile"):
                self.add_required_key(lib, "fileset", fileset, "file", "commandfile")
            if lib.has_file(fileset=fileset, filetype="systemverilog"):
                self.add_required_key(lib, "fileset", fileset, "file", "systemverilog")
            if lib.has_file(fileset=fileset, filetype="verilog"):
                self.add_required_key(lib, "fileset", fileset, "file", "verilog")

        fileset = self.project.get("option", "fileset")[0]
        design = self.project.design
        for param in design.getkeys("fileset", fileset, "param"):
            self.add_required_key(design, "fileset", fileset, "param", param)

    def runtime_options(self):
        options = super().runtime_options()

        options.append('--single-unit')

        options.extend(['--threads', self.get("threads")])

        filesets = self.project.get_filesets()
        idirs = []
        defines = []
        undefines = []
        for lib, fileset in filesets:
            idirs.extend(lib.get_idir(fileset))
            defines.extend(lib.get("fileset", fileset, "define"))
            undefines.extend(lib.get("fileset", fileset, "undefine"))

        params = []
        fileset = self.project.get("option", "fileset")[0]
        design = self.project.design
        for param in design.getkeys("fileset", fileset, "param"):
            params.append((param, design.get("fileset", fileset, "param", param)))

        #####################
        # Include paths
        #####################
        if idirs:
            options.extend(['--include-directory', f'{",".join(idirs)}'])

        #######################
        # Variable Definitions
        #######################
        for value in defines:
            options.extend(['-D', value])

        #######################
        # Variable Undefinitions
        #######################
        for value in undefines:
            options.extend(['-U', value])

        #######################
        # Command files
        #######################
        cmdfiles = []
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="commandfile"):
                cmdfiles.append(value)
        if cmdfiles:
            options.extend(['-F', f'{",".join(cmdfiles)}'])

        #######################
        # Sources
        #######################
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="systemverilog"):
                options.append(value)
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="verilog"):
                options.append(value)

        #######################
        # Top Module
        #######################
        options.extend(['--top', self.design_topmodule])

        ###############################
        # Parameters (top module only)
        ###############################
        # Set up user-provided parameters to ensure we elaborate the correct modules
        for param, value in params:
            options.extend(['-G', f'{param}={value}'])

        return options

    def _init_driver(self, ignored_diagnotics=None):
        self._driver = pyslang.Driver()
        self._driver.addStandardArgs()

        parse_options = pyslang.CommandLineOptions()
        parse_options.ignoreProgramName = True
        opts = shlex.join(self.get_runtime_arguments())
        self.logger.info(f"runtime arguments: {opts}")
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
                self.logger.warning(f'{warning} is not a valid slang category')

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
                self.logger.warning(line)
        if report["error"]:
            for line in report["error"]:
                self.logger.error(line)

        diags.clearCounts()
        for diag in self._compilation.getAllDiagnostics():
            diags.issue(diag)

        self.record_metric("errors", diags.numErrors, source_file=self.get_logpath("sc"))
        self.record_metric("warnings", diags.numWarnings, source_file=self.get_logpath("sc"))
