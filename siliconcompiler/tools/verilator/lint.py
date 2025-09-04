from siliconcompiler.tools.verilator import VerilatorTask


class LintTask(VerilatorTask):
    def task(self):
        return "lint"

    def runtime_options(self):
        options = super().runtime_options()
        options.append('--lint-only')
        options.append('--no-timing')
        return options
