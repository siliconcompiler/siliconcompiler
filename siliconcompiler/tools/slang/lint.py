'''
Lint system verilog
'''
from siliconcompiler.tools import slang
from siliconcompiler.tools._common import get_tool_task
import os


def setup(chip):
    slang.setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             clobber=False, step=step, index=index)


def run(chip):
    driver, exitcode = slang._get_driver(chip, runtime_options)
    if exitcode:
        return exitcode

    _, ok = slang._compile(chip, driver)

    if ok:
        return 0
    else:
        return 1


def runtime_options(chip):
    options = slang.runtime_options(chip)

    options.append("--lint-only")

    return options
