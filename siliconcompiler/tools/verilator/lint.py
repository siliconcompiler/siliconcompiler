from siliconcompiler.tools.verilator.verilator import setup as setup_tool
from siliconcompiler.tools.verilator.verilator import runtime_options as runtime_options_tool


def setup(chip):
    '''
    Lints Verilog source. Results of linting can be programmatically queried
    using errors/warnings metrics.
    '''

    # Generic tool setup.
    setup_tool(chip)


def runtime_options(chip):
    cmdlist = runtime_options_tool(chip)
    cmdlist.append('--lint-only')
    cmdlist.append('--no-timing')
    return cmdlist
