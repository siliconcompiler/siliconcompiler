from siliconcompiler import utils
from siliconcompiler.tools import slang
from siliconcompiler.tools._common import get_tool_task


from siliconcompiler.tool import FrontendTask


class Lint(FrontendTask):
    def tool(self):
        return "slang"

    def task(self):
        return "lint"

    def setup(self):
        super().setup()

        if slang.test_version():
            return slang.test_version()

        self.set("threads", utils.get_cores(None), clobber=False)

    def run(self):
        def tmp(*args):
            return self.get_files("rtl", "verilog")
        driver, exitcode = slang._get_driver(self._parent(root=True), tmp)
        if exitcode:
            return exitcode

        compilation, ok = slang._compile(self._parent(root=True), driver)
        slang._diagnostics(self._parent(root=True), driver, compilation)

        if ok:
            return 0
        else:
            return 1


def setup(chip):
    '''
    Lint system verilog
    '''
    if slang.test_version():
        return slang.test_version()

    slang.setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             clobber=False, step=step, index=index)


def run(chip):
    driver, exitcode = slang._get_driver(chip, runtime_options)
    if exitcode:
        return exitcode

    compilation, ok = slang._compile(chip, driver)
    slang._diagnostics(chip, driver, compilation)

    if ok:
        return 0
    else:
        return 1


def runtime_options(chip):
    options = slang.common_runtime_options(chip)
    options.extend([
        "-Weverything"
    ])

    return options
