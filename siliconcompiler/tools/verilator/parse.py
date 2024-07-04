from siliconcompiler.tools.verilator.verilator import setup as setup_tool
from siliconcompiler.tools.verilator.verilator import runtime_options as runtime_options_tool
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''
    Lints Verilog source. Results of linting can be programmatically queried
    using errors/warnings metrics.
    '''

    # Generic tool setup.
    setup_tool(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'output', f'{chip.top()}.v',
             step=step, index=index)


def runtime_options(chip):
    cmdlist = runtime_options_tool(chip)
    cmdlist.append('--xml-only')
    cmdlist.append('--no-timing')
    return cmdlist
