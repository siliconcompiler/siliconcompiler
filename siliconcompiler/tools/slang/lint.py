from siliconcompiler.tools.slang import SlangTask


class Lint(SlangTask):
    '''
    Lint system verilog
    '''
    def task(self):
        return "lint"

    def runtime_options(self):
        options = super().runtime_options()
        options.extend([
            "-Weverything"
        ])
        return options

    def run(self):
        self._init_driver()
        if self._error_code:
            return self._error_code

        ok = self._compile()
        self._diagnostics()

        if ok:
            return 0
        else:
            return 1
