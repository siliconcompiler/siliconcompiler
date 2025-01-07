from siliconcompiler import utils
from siliconcompiler.tools import slang
from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_tool_task


def setup(chip):
    '''
    Lint system verilog
    '''
    slang.setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             clobber=False, step=step, index=index)

    add_require_input(chip, 'input', 'rtl', 'verilog')
    add_require_input(chip, 'input', 'rtl', 'systemverilog')
    add_frontend_requires(chip, ['ydir', 'idir', 'vlib', 'libext', 'define', 'param'])


def runtime_options(chip):
    options = slang.common_runtime_options(chip)
    options.extend([
        "--lint-only"
    ])

    return options


def post_process(chip):
    slang.post_process(chip)
