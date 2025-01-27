from siliconcompiler import utils
from siliconcompiler.tools import slang
from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_tool_task, has_input_files


def setup(chip):
    '''
    Elaborate verilog design files and generate a unified file.
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

    chip.set('tool', tool, 'task', task, 'stdout', 'destination', 'output', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'stdout', 'suffix', 'v', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'output', __outputfile(chip), step=step, index=index)


def runtime_options(chip):
    options = slang.common_runtime_options(chip)
    options.extend([
        "--preprocess",
        "--comments",
        "--ignore-unknown-modules",
        "--allow-use-before-declare"
    ])

    return options


def __outputfile(chip):
    is_systemverilog = has_input_files(chip, 'input', 'rtl', 'systemverilog')
    if is_systemverilog:
        return f'{chip.top()}.sv'
    return f'{chip.top()}.v'
